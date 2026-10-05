#!/bin/sh
# Run the backend tests inside the backend Docker image (Python 3.11, Tesseract, CPU torch)
# against the compose Postgres (pgvector) and MinIO services, then optionally tear down.
#   backend/scripts/test_services.sh                  # all tests except hf_model / llm_live
#   backend/scripts/test_services.sh -m hf_model      # extra pytest args are passed through
#   KEEP_SERVICES=0 backend/scripts/test_services.sh  # `docker compose down` afterwards
# Requires the repo-root .env (copied from .env.example) with MINIO_APP_SECRET_KEY and
# TEST_MINIO_SECRET_KEY set (minio-init creates the app and test users from them).
# Pure unit tests only (no Docker):
#   pytest -m "not pg and not minio and not tesseract and not hf_model and not llm_live"
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "Missing $ROOT/.env - copy .env.example, then set MINIO_APP_SECRET_KEY and TEST_MINIO_SECRET_KEY." >&2
  exit 2
fi

# Read one value from .env without sourcing it (some values contain spaces).
env_value() {
  grep -E "^$1=" .env | tail -n 1 | cut -d= -f2-
}

if [ -z "$(env_value TEST_MINIO_SECRET_KEY)" ]; then
  echo "Set TEST_MINIO_SECRET_KEY in $ROOT/.env (the MinIO test user is created from it)." >&2
  exit 2
fi
ROOT_USER="$(env_value MINIO_ROOT_USER)"
ROOT_PASSWORD="$(env_value MINIO_ROOT_PASSWORD)"

docker compose up -d --wait postgres minio
docker compose run --rm minio-init
docker compose build backend

if [ "$#" -eq 0 ]; then
  set -- -m "not hf_model and not llm_live"
fi

set +e
# TEST_MINIO_ACCESS_KEY / TEST_MINIO_SECRET_KEY reach the container through .env (env_file).
# The root credential is blanked for backend/celery, so the tests' cleanup client gets it here.
docker compose run --rm --no-deps \
  -e TEST_DATABASE_URL=postgresql+psycopg://uniadapt:uniadapt@postgres:5432/uniadapt_test \
  -e TEST_MINIO_ENDPOINT=minio:9000 \
  -e TEST_MINIO_ROOT_USER="${ROOT_USER:-minioadmin}" \
  -e TEST_MINIO_ROOT_PASSWORD="${ROOT_PASSWORD:-minioadmin}" \
  backend sh -c 'pip install -q -e ".[dev]" && python -m pytest "$@"' pytest "$@"
STATUS=$?
set -e

if [ "${KEEP_SERVICES:-1}" = "0" ]; then
  docker compose down
fi
exit $STATUS
