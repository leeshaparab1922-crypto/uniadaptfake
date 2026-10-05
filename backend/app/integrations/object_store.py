"""MinIO object store (ADR-0018; client library `minio`, plan P-2).

- single private bucket (name from config);
- key `subjects/{subject_id}/assets/{content_asset_id}/versions/{content_version_id}/original.{ext}`
  where `ext` comes from the *validated* type, never the uploaded filename;
- write-once: `put_if_absent` refuses to overwrite an existing key;
- the app uses a scoped service credential, not the root key (NFR-SEC-013);
- no derived artifacts are stored here (extracted text/chunks live in PostgreSQL).
"""

from __future__ import annotations

import uuid
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.services.ingestion.ports import ObjectAlreadyExistsError

ALLOWED_KEY_EXTENSIONS = ("pdf", "pptx", "docx", "txt")


def build_storage_key(
    subject_id: uuid.UUID | str,
    content_asset_id: uuid.UUID | str,
    content_version_id: uuid.UUID | str,
    ext: str,
) -> str:
    """ADR-0018 key layout. IDs are re-parsed as UUIDs so no user text can reach a key."""
    if ext not in ALLOWED_KEY_EXTENSIONS:
        raise ValueError(f"Unsupported extension for storage key: {ext!r}")
    sid, aid, vid = (uuid.UUID(str(v)) for v in (subject_id, content_asset_id, content_version_id))
    return f"subjects/{sid}/assets/{aid}/versions/{vid}/original.{ext}"


class MinioObjectStore:
    def __init__(self, client: Minio, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    @classmethod
    def from_settings(cls) -> MinioObjectStore:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.effective_minio_access_key,
            secret_key=settings.effective_minio_secret_key,
            secure=settings.minio_secure,
        )
        return cls(client, settings.minio_bucket)

    @property
    def bucket(self) -> str:
        return self._bucket

    def exists(self, key: str) -> bool:
        try:
            self._client.stat_object(self._bucket, key)
            return True
        except S3Error as exc:
            if exc.code in ("NoSuchKey", "NoSuchObject", "NotFound"):
                return False
            raise

    def put_if_absent(self, key: str, data: BinaryIO, size: int, content_type: str) -> None:
        # Keys embed a fresh content_version_id UUID, so collisions are impossible in
        # normal operation; this guard enforces ADR-0018's "never re-put an existing key".
        if self.exists(key):
            raise ObjectAlreadyExistsError(key)
        self._client.put_object(self._bucket, key, data, length=size, content_type=content_type)

    def download_to(self, key: str, dest_path: str) -> None:
        self._client.fget_object(self._bucket, key, dest_path)

    def stat_size(self, key: str) -> int:
        return int(self._client.stat_object(self._bucket, key).size or 0)
