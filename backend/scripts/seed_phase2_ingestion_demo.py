"""Demo data for Phase 2 slice 2A (NFR-TST-002): uploads a small synthetic syllabus
and one notes file for the first seeded Subject through the real service layer,
ingests them, and activates the syllabus as the Subject Owner.

Prerequisites: the Phase 1 seed (`python -m scripts.seed_demo_data`), running
Postgres + MinIO (compose), `alembic upgrade head`, and the bootstrap bucket.
Uses the real local embedding model, so the first run downloads bge-m3.

Run with: `python -m scripts.seed_phase2_ingestion_demo` from `backend/`.
Idempotent: skips when the Subject already has a syllabus asset.
"""

from __future__ import annotations

import os
import tempfile

from sqlalchemy import select

from app.db.session import SessionLocal
from app.integrations.embedding import BgeM3Embedder
from app.integrations.object_store import MinioObjectStore
from app.integrations.ocr import TesseractOcrEngine
from app.integrations.tokenizer import BgeM3Tokenizer
from app.models.content import ContentAsset, ContentType
from app.models.subject import Subject
from app.models.subject_instance import SubjectOwnerAssignment
from app.models.user import User
from app.services import content_service
from app.services.ingestion_runtime import ingest_version

SYLLABUS_TEXT = """Unit 1: Introduction to Data Structures
Arrays, linked lists, stacks and queues. Time and space complexity.

Unit 2: Trees and Graphs
Binary trees, binary search trees, traversals. Graph representations, BFS and DFS.

Unit 3: Sorting and Searching
Bubble, merge and quick sort. Linear and binary search. Hashing.
"""


class _InlineQueue:
    def enqueue(self, content_version_id: str) -> None:  # the seed ingests synchronously instead
        return None


def main() -> None:
    store = MinioObjectStore.from_settings()
    ocr, tokenizer, embedder = TesseractOcrEngine(), BgeM3Tokenizer(), BgeM3Embedder()
    with SessionLocal() as db:
        subject = db.scalars(select(Subject).order_by(Subject.code)).first()
        if subject is None:
            raise SystemExit("Run `python -m scripts.seed_demo_data` first.")
        if db.scalar(
            select(ContentAsset.id).where(
                ContentAsset.subject_id == subject.id, ContentAsset.content_type == ContentType.SYLLABUS
            )
        ):
            print("Demo syllabus already present; nothing to do.")
            return
        owner_row = db.scalar(
            select(SubjectOwnerAssignment).where(SubjectOwnerAssignment.subject_id == subject.id)
        )
        if owner_row is None:
            raise SystemExit("The demo Subject has no Subject Owner; seed owners first.")
        owner = db.get(User, owner_row.owner_teacher_id)

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "syllabus.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(SYLLABUS_TEXT)
            version = content_service.upload_content(
                db,
                actor=owner,
                subject_id=subject.id,
                content_type=ContentType.SYLLABUS,
                title="Syllabus",
                unit_id=None,
                content_asset_id=None,
                original_filename="syllabus.txt",
                declared_content_type="text/plain",
                local_path=path,
                store=store,
                queue=_InlineQueue(),
            )
        result = ingest_version(db, version.id, store=store, ocr=ocr, tokenizer=tokenizer, embedder=embedder)
        print(f"Ingestion: {result.status} ({result.chunk_count} chunks)")
        if result.status == "SUCCEEDED":
            content_service.activate_version(db, actor=owner, version_id=version.id, reason="Demo seed")
            print("Syllabus activated by the Subject Owner.")


if __name__ == "__main__":
    main()
