"""Environment-driven settings (Pydantic v2 Settings).

python-dotenv loads `.env` in local development only (ADR-0010); in Docker
and production, real environment variables are used instead.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_JWT_SECRET = "change-me-in-env"
MIN_JWT_SECRET_BYTES = 32
_NON_PRODUCTION_ENVIRONMENTS = {"development", "test"}
_MINIO_APP_KEY_HINT = (
    "{name} must be set: the app only uses the scoped MinIO credential created by "
    "`docker compose run --rm minio-init` (ADR-0018), never the root credential."
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+psycopg://uniadapt:uniadapt@localhost:5432/uniadapt"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 240  # NFR-SEC-004: 4-hour access token, no refresh token.

    bcrypt_rounds: int = 12

    cookie_secure: bool = True  # Disable only for local HTTP development.
    cookie_domain: str | None = None
    cors_allowed_origin: str = "http://localhost:5173"

    # ADR-0006: fixed-window rate limiting, limits/window configurable via env, not hard-coded.
    rate_limit_window_seconds: int = 900
    rate_limit_login_per_account_per_window: int = 5
    rate_limit_login_per_ip_per_window: int = 20
    rate_limit_token_consume_per_ip_per_window: int = 20

    invitation_token_ttl_hours: int = 72
    password_reset_token_ttl_hours: int = 2

    minio_endpoint: str = "localhost:9000"
    minio_secure: bool = False
    # ADR-0018: one private bucket; the app uses a scoped credential, never the root key.
    minio_bucket: str = "uniadapt-content"
    minio_app_access_key: str = ""
    minio_app_secret_key: str = ""

    # --- Upload limits (SRS Section 17, NFR-SEC-009; plan P-12) ---
    upload_max_bytes: int = 25 * 1024 * 1024
    rate_limit_upload_per_teacher_per_window: int = 30

    # --- Ingestion (plan P-4: approved defaults; ADR-0013/0014) ---
    ingest_min_page_chars: int = 25  # a page "has usable text" at >= this many non-whitespace chars
    ocr_language: str = "eng"
    ocr_tesseract_config: str = "--oem 1 --psm 3"
    ocr_render_dpi: int = 300
    ocr_min_mean_confidence: float = 60.0
    ocr_min_chars: int = 25
    ocr_blank_page_ink_ratio: float = 0.001  # fraction of non-white pixels below which a page is blank
    ingest_pptx_notes: bool = True  # plan P-5
    ingest_max_attempts: int = 3

    # --- Ingestion job and input limits (finding M5; human-approved defaults 2026-10-04) ---
    ingest_task_time_limit_seconds: int = 30 * 60  # hard Celery time limit per ingestion job
    ingest_task_soft_time_limit_seconds: int = 25 * 60  # graceful stop: version marked FAILED
    ingest_max_pdf_pages: int = 500
    ingest_archive_max_uncompressed_bytes: int = 200 * 1024 * 1024  # PPTX/DOCX unpacked size
    ingest_archive_max_compression_ratio: float = 100.0
    ingest_archive_max_members: int = 2000
    # A RUNNING version with no stage activity for this long may be retried (finding M2).
    # 0 means "job time limit + 10 minutes".
    ingest_stale_after_seconds: int = 0

    # --- Embeddings (ADR-0015). Revision is pinned (plan P-9, resolved 2026-10-02). ---
    embedding_model_id: str = "BAAI/bge-m3"
    embedding_model_revision: str = "5617a9f61b028005a4858fdac845db406aefb181"
    embedding_batch_size: int = 16
    chunk_max_tokens: int = 800
    chunk_overlap_tokens: int = 120
    hf_home: str | None = None

    # --- Curriculum Agent / LLM provider (slice 2B; ADR-0016, ADR-0017, plan P-3/P-14/P-15) ---
    llm_provider: str = "ANTHROPIC"
    llm_model: str = "claude-opus-5-5"  # ADR-0016 default; deployment configuration, not code
    llm_effort: str = "medium"  # thinking cannot be disabled; effort is set and recorded explicitly
    llm_max_output_tokens: int = 32000
    llm_token_budget: int = 400000  # per-run input+output budget (Section 18 "token budget")
    llm_repair_attempts: int = 2  # bounded retry-with-repair loop for schema-invalid output
    llm_request_timeout_seconds: int = 600
    anthropic_api_key: str = ""  # from the environment only (NFR-SEC-013); never committed
    rate_limit_generate_per_teacher_per_window: int = 10
    prompt_sync_on_startup: bool = True  # ADR-0017 startup sync; tests turn it off for SQLite apps
    # ADR-0020: 0.72 for bge-m3 (the SRS initial 0.92 failed validation); must be VALIDATED (BUS-050)
    duplicate_threshold_default: str = "0.720"
    fallback_topic_est_hours: float = 1.0  # flat Unit-order fallback Topics (FR-CUR-004)
    curriculum_generation_max_attempts: int = 3
    # Curriculum job limits (verification finding D1). 0 = derived from the LLM call budget:
    # soft = timeout x (1 + repair attempts) + 5 min, hard = soft + 5 min,
    # stale GENERATING = hard + 20 min (covers the retry back-off between attempts).
    curriculum_task_soft_time_limit_seconds: int = 0
    curriculum_task_time_limit_seconds: int = 0
    curriculum_generation_stale_after_seconds: int = 0
    celery_broker_url: str | None = None  # defaults to redis_url

    @property
    def effective_curriculum_soft_time_limit_seconds(self) -> int:
        if self.curriculum_task_soft_time_limit_seconds > 0:
            return self.curriculum_task_soft_time_limit_seconds
        return self.llm_request_timeout_seconds * (1 + self.llm_repair_attempts) + 5 * 60

    @property
    def effective_curriculum_time_limit_seconds(self) -> int:
        if self.curriculum_task_time_limit_seconds > 0:
            return self.curriculum_task_time_limit_seconds
        return self.effective_curriculum_soft_time_limit_seconds + 5 * 60

    @property
    def effective_curriculum_stale_after_seconds(self) -> int:
        if self.curriculum_generation_stale_after_seconds > 0:
            return self.curriculum_generation_stale_after_seconds
        return self.effective_curriculum_time_limit_seconds + 20 * 60

    @property
    def effective_ingest_stale_after_seconds(self) -> int:
        if self.ingest_stale_after_seconds > 0:
            return self.ingest_stale_after_seconds
        return self.ingest_task_time_limit_seconds + 10 * 60

    @property
    def effective_minio_access_key(self) -> str:
        """The scoped app credential (ADR-0018 rule 4 / NFR-SEC-013). There is no fallback to
        the MinIO root credential in any environment, including development and test."""
        if self.minio_app_access_key:
            return self.minio_app_access_key
        raise ValueError(_MINIO_APP_KEY_HINT.format(name="MINIO_APP_ACCESS_KEY"))

    @property
    def effective_minio_secret_key(self) -> str:
        if self.minio_app_secret_key:
            return self.minio_app_secret_key
        raise ValueError(_MINIO_APP_KEY_HINT.format(name="MINIO_APP_SECRET_KEY"))

    @property
    def effective_celery_broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @model_validator(mode="after")
    def _reject_weak_jwt_secret_outside_dev_test(self) -> Settings:
        """NFR-SEC-004/013: a 4-hour JWT signed with a short or placeholder
        secret is trivially forgeable. Refuse to start with one outside
        development/test - `.env.example` documents the required override."""
        if self.environment.lower() not in _NON_PRODUCTION_ENVIRONMENTS:
            if self.jwt_secret_key == PLACEHOLDER_JWT_SECRET:
                raise ValueError(
                    "JWT_SECRET_KEY is still the placeholder value; set a real "
                    "secret before starting outside development/test."
                )
            if len(self.jwt_secret_key.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
                raise ValueError(
                    f"JWT_SECRET_KEY must be at least {MIN_JWT_SECRET_BYTES} bytes "
                    "outside development/test."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
