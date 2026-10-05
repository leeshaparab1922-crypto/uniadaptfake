"""Demo for Phase 2 slice 2B (NFR-TST-002) - the Section 43 story, with a STUB model (no key):

  cyclic syllabus draft (A->B 0.8, B->A 0.4) -> the 0.4 edge is dropped and flagged ->
  a CO Teacher edits (rename) but cannot approve -> the Subject Owner approves -> ACTIVE.

Prerequisites: Phase 1 seed, `seed_phase2_ingestion_demo` (an ACTIVE syllabus), `seed_curriculum_config`,
and an ACTIVE duplicate threshold (`validate_similarity_threshold --activate`); otherwise approval
is correctly blocked and the script says so. Uses the real local embedding model.

Run with: `python -m scripts.seed_phase2_curriculum_demo` from `backend/`. Idempotent per Subject.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.agents.curriculum_runner import run_generation
from app.core.errors import ConflictError, ForbiddenError
from app.db.session import SessionLocal
from app.integrations.embedding import BgeM3Embedder
from app.integrations.llm.base import LLMRequest, LLMResponse
from app.models.curriculum import CurriculumOrigin, CurriculumStatus, CurriculumVersion
from app.models.subject import Subject
from app.models.subject_instance import SubjectInstance, SubjectOwnerAssignment, TeacherAssignment
from app.models.user import User
from app.prompts.registry import sync_prompts
from app.services import curriculum_edit_service as edits
from app.services import curriculum_service as cs

CYCLIC = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "curriculum" / "cyclic.json"


class _StubProvider:
    name = "STUB"

    def generate_structured(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(CYCLIC.read_text(encoding="utf-8"), "end_turn", 0, 0)


class _NoQueue:
    def enqueue(self, curriculum_version_id: str) -> None:
        return None


def main() -> None:
    embedder = BgeM3Embedder()
    with SessionLocal() as db:
        sync_prompts(db)
        subject = db.scalars(select(Subject).order_by(Subject.code)).first()
        if subject is None:
            raise SystemExit("Run the Phase 1 and slice 2A demo seeds first.")
        # Idempotent: skip only when the demo's AI-origin version already exists. A failed attempt or
        # an ACTIVE flat fallback does not count; the fallback becomes the "prior active chain".
        if db.scalar(
            select(CurriculumVersion.id).where(
                CurriculumVersion.subject_id == subject.id,
                CurriculumVersion.origin == CurriculumOrigin.AGENT,
                CurriculumVersion.status != CurriculumStatus.GENERATION_FAILED,
            )
        ):
            print("This Subject already has the demo curriculum; nothing to do.")
            return
        prior_active = db.scalar(
            select(CurriculumVersion).where(
                CurriculumVersion.subject_id == subject.id,
                CurriculumVersion.status == CurriculumStatus.ACTIVE,
            )
        )
        owner = db.get(
            User,
            db.scalar(
                select(SubjectOwnerAssignment.owner_teacher_id).where(
                    SubjectOwnerAssignment.subject_id == subject.id
                )
            ),
        )
        co_id = db.scalar(
            select(TeacherAssignment.teacher_id)
            .join(SubjectInstance, SubjectInstance.id == TeacherAssignment.subject_instance_id)
            .where(SubjectInstance.subject_id == subject.id, TeacherAssignment.teacher_id != owner.id)
        )
        co = db.get(User, co_id) if co_id else None

        cv = cs.request_generation(db, actor=owner, subject_id=subject.id, queue=_NoQueue())
        outcome = run_generation(db, cv.id, provider=_StubProvider(), embedder=embedder)
        print(f"Generation: {outcome.status}")
        view = cs.build_graph_view(db, owner, cv.id)
        print(f"Dropped edges: {[(e.edge.drop_reason) for e in view.edges if e.edge.dropped]}")

        if co is not None:
            first = view.topics[0].version
            edits.update_topic(
                db,
                actor=co,
                curriculum_version_id=cv.id,
                topic_id=first.topic_id,
                changes={"name": first.name + " (reviewed)"},
                embedder=embedder,
            )
            print("CO Teacher edited a Topic.")
            try:
                cs.approve_version(db, actor=co, curriculum_version_id=cv.id, reason="should fail")
            except ForbiddenError as exc:
                print(f"CO approval correctly refused: {exc}")
        try:
            cs.approve_version(db, actor=owner, curriculum_version_id=cv.id, reason="Demo approval")
            print("Owner approved; curriculum ACTIVE.")
            if prior_active is not None:
                db.refresh(prior_active)
                prior_view = cs.build_graph_view(db, owner, prior_active.id)
                print(
                    f"Prior active v{prior_active.version_no} is now {prior_active.status.value} and still "
                    f"resolvable ({len(prior_view.topics)} Topics)."
                )
        except ConflictError as exc:
            print(f"Owner approval blocked (expected until the threshold is validated): {exc}")
        print(json.dumps({"curriculum_version_id": str(cv.id)}))


if __name__ == "__main__":
    main()
