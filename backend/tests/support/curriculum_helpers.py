"""Shared setup for slice 2B PostgreSQL tests (service layer, fake LLM, fake embedder)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.agents.curriculum_runner import GenerationOutcome, run_generation
from app.models.content import ContentType, ContentVersion, ContentVersionStatus, IngestionStatus
from app.models.curriculum import CurriculumVersion, SimilarityThreshold
from app.prompts.registry import sync_prompts
from app.services import curriculum_service as cs
from app.services import similarity_config_service as thresholds
from app.services.embedding_config_service import get_or_create_active_config
from tests.support.content_helpers import make_asset, make_chunk, make_embedding_config, make_version
from tests.support.fakes import FakeEmbedder, RecordingQueue
from tests.support.llm import FakeLLMProvider, fixture_text
from tests.support.world import World, build_world


@dataclass
class Setup:
    world: World
    syllabus: ContentVersion
    chunk_ids: list


def add_active_syllabus(db: Session, world: World) -> Setup:
    asset = make_asset(
        db,
        subject_id=world.subject.id,
        actor=world.owner,
        content_type=ContentType.SYLLABUS,
        title="Syllabus",
    )
    version = make_version(
        db,
        asset=asset,
        actor=world.owner,
        version_no=1,
        status=ContentVersionStatus.ACTIVE,
        ingestion=IngestionStatus.SUCCEEDED,
    )
    config = make_embedding_config(db)
    chunks = [
        make_chunk(
            db,
            version=version,
            subject_id=world.subject.id,
            config=config,
            index=i,
            text=f"Unit {i + 1} syllabus text {i}",
            unit_no=i + 1,
            chunk_type=ContentType.SYLLABUS,
        )
        for i in range(3)
    ]
    db.commit()
    return Setup(world, version, [c.id for c in chunks])


def activate_validated_threshold(db: Session) -> SimilarityThreshold:
    """An ACTIVE (validated) duplicate threshold for the current embedding configuration."""
    config = get_or_create_active_config(db)
    row = thresholds.resolve_threshold(db, config)
    thresholds.record_validation(db, row.id, report={"passed": True, "test": True}, passed=True)
    return thresholds.activate_threshold(db, row.id)


def prepare(db: Session, *, threshold_active: bool = True) -> Setup:
    sync_prompts(db)
    world = build_world(db)
    setup = add_active_syllabus(db, world)
    if threshold_active:
        activate_validated_threshold(db)
    return setup


def generate(
    db: Session,
    setup: Setup,
    *,
    fixture: str = "cyclic",
    llm: FakeLLMProvider | None = None,
    embedder=None,
    actor=None,
) -> tuple[CurriculumVersion, GenerationOutcome]:
    queue = RecordingQueue()
    cv = cs.request_generation(
        db, actor=actor or setup.world.co, subject_id=setup.world.subject.id, queue=queue
    )
    assert queue.enqueued == [str(cv.id)]
    outcome = run_generation(
        db,
        cv.id,
        provider=llm or FakeLLMProvider(fixture_text(fixture)),
        embedder=embedder or FakeEmbedder(),
    )
    db.refresh(cv)
    return cv, outcome


def topic_ids_by_name(db: Session, cv: CurriculumVersion, viewer) -> dict[str, object]:
    view = cs.build_graph_view(db, viewer, cv.id)
    return {t.version.name: t.version.topic_id for t in view.topics}


class ScriptedEmbedder:
    """Returns prescribed 1024-d unit vectors keyed by Topic name (the first line of the text)."""

    dimension = 1024

    def __init__(self, vectors: dict[str, list[float]] | None = None) -> None:
        self.vectors = vectors or {}
        self.calls = 0
        self.texts: list[str] = []

    @staticmethod
    def with_cosine(cos: float) -> list[float]:
        import math

        vec = [0.0] * 1024
        vec[0], vec[1] = cos, math.sqrt(max(0.0, 1 - cos * cos))
        return vec

    def embed(self, texts):
        self.calls += 1
        self.texts.extend(texts)
        out = []
        for text in texts:
            name = text.split("\n", 1)[0]
            out.append(self.vectors.get(name) or FakeEmbedder.vector_for(text))
        return out


def add_active_curriculum(db: Session, subject, actor, names: list[str], *, units: list | None = None):
    """An ACTIVE curriculum with simple Topics for `subject`, inserted directly (earlier-semester
    Subject fixtures for cross-subject scope tests)."""
    from sqlalchemy import select

    from app.models.curriculum import (
        BloomLevel,
        CurriculumOrigin,
        CurriculumStatus,
        Topic,
        TopicClassification,
        TopicVersion,
        ValidationStatus,
    )
    from app.models.subject import Unit

    unit = (units or list(db.scalars(select(Unit).where(Unit.subject_id == subject.id))))[0]
    cv = CurriculumVersion(
        subject_id=subject.id,
        version_no=1,
        status=CurriculumStatus.ACTIVE,
        origin=CurriculumOrigin.AGENT,
        revision=1,
        validated_revision=1,
        validation_status=ValidationStatus.PASSED,
        created_by=actor.id,
    )
    db.add(cv)
    db.flush()
    topics = []
    for i, name in enumerate(names, start=1):
        topic = Topic(subject_id=subject.id)
        db.add(topic)
        db.flush()
        db.add(
            TopicVersion(
                topic_id=topic.id,
                curriculum_version_id=cv.id,
                unit_id=unit.id,
                name=name,
                outcomes=["Know it"],
                bloom_level=BloomLevel.REMEMBER,
                est_hours=1,
                classification=TopicClassification.CORE,
                order_index=i,
            )
        )
        topics.append(topic)
    db.commit()
    return cv, topics


def add_subject(db: Session, world: World, *, semester_no: int, code: str):
    """A second Subject in the same Program (with one Unit) at the given semester."""
    from app.models.subject import SubjectType
    from app.services import subject_service

    subject = subject_service.create_subject(
        db,
        actor=world.admin,
        program_id=world.program_id,
        semester_no=semester_no,
        code=code,
        name=f"Subject {code}",
        credits=3,
        type_=SubjectType.CORE,
        elective_group_id=None,
    )
    subject_service.set_units(
        db,
        actor=world.admin,
        subject_id=subject.id,
        units=[{"order_index": 1, "name": "Only", "weightage": 100}],
    )
    db.commit()
    return subject
