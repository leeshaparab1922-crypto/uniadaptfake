#!/bin/sh
# Idempotent MinIO bootstrap for ADR-0018 (run by the one-shot `minio-init` compose service,
# image minio/mc - ADR-0019). Safe to run again.
#
# - Creates the private content bucket and a policy limited to it (get/put/list only: the app
#   never deletes or overwrites, ADR-0018 write-once), attached to the scoped app user that
#   backend/celery use (NFR-SEC-013). The app policy covers ONLY the content bucket.
# - If MINIO_TEST_SECRET_KEY is set, also creates the test bucket and a separate test user whose
#   policy covers ONLY the test bucket (finding N6).
#
# Required env: MINIO_ENDPOINT_URL, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, MINIO_BUCKET,
#               MINIO_APP_ACCESS_KEY, MINIO_APP_SECRET_KEY.
# Optional env: MINIO_TEST_BUCKET, MINIO_TEST_ACCESS_KEY, MINIO_TEST_SECRET_KEY.
set -eu

mc alias set local "$MINIO_ENDPOINT_URL" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

# setup_scoped <bucket> <policy-name> <access-key> <secret-key>
setup_scoped() {
  bucket="$1"
  policy="$2"
  access="$3"
  secret="$4"

  mc mb --ignore-existing "local/$bucket"
  mc anonymous set none "local/$bucket"

  cat > "/tmp/$policy.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": ["arn:aws:s3:::$bucket", "arn:aws:s3:::$bucket/*"]
    }
  ]
}
EOF
  mc admin policy create local "$policy" "/tmp/$policy.json"
  mc admin user add local "$access" "$secret"

  # Attach only when missing; a real attach failure must fail the bootstrap (no `|| true`).
  if mc admin user info local "$access" | grep -qw "$policy"; then
    echo "Policy $policy already attached to $access"
  else
    mc admin policy attach local "$policy" --user "$access"
  fi
  if ! mc admin user info local "$access" | grep -qw "$policy"; then
    echo "Policy $policy is not attached to $access" >&2
    exit 1
  fi
}

setup_scoped "$MINIO_BUCKET" uniadapt-content-rw "$MINIO_APP_ACCESS_KEY" "$MINIO_APP_SECRET_KEY"
echo "MinIO bootstrap complete for $MINIO_BUCKET (app user $MINIO_APP_ACCESS_KEY)"

if [ -n "${MINIO_TEST_SECRET_KEY:-}" ]; then
  setup_scoped "${MINIO_TEST_BUCKET:-uniadapt-content-test}" uniadapt-content-test-rw \
    "${MINIO_TEST_ACCESS_KEY:-uniadapt-test}" "$MINIO_TEST_SECRET_KEY"
  echo "MinIO test bucket ready (test user ${MINIO_TEST_ACCESS_KEY:-uniadapt-test})"
fi
