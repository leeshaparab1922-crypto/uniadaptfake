# ADR-0018: MinIO bucket and object-key layout for uploaded content

- **Status:** Accepted
- **Date:** 2026-10-02
- **Affects:** Phase 2 (upload, ingestion, rollback); Phase 8 (material viewer / citation download); Phase 9 (retention and disposal jobs)
- **SRS refs:** FR-CON-001; FR-CON-002 ("File in MinIO"); FR-CON-004; Section 17 "Storage" and "Versioning" rows; Section 31.2 ContentAsset / ContentVersion ("storage key"); BUS-039; NFR-DAT-002; NFR-SEC-007; NFR-SEC-013; NFR-SEC-014

## Context
- Original files go to MinIO. Records go to PostgreSQL, and vectors go to
  pgvector (Section 17).
- An upload **never overwrites**. Active content is immutable, and earlier
  versions must stay resolvable after a rollback or replacement (FR-CON-004,
  BUS-039, NFR-DAT-002).
- Teachers may see content only for Subjects they are assigned to
  (NFR-SEC-007). Stored files need least-privilege service credentials
  (NFR-SEC-013), and records have retention and disposal rules
  (NFR-SEC-014).
- `docker-compose.yml` already runs MinIO with the default root credentials.
  The SRS does not define buckets or key structure.

## Options

### A. One private bucket, hierarchical keys by ID (recommended)
Bucket `uniadapt-content`. Key:
`subjects/{subject_id}/assets/{content_asset_id}/versions/{content_version_id}/original.{ext}`
- **Pros:** The key matches the data model in Section 31.2, so an object is
  easy to trace to its Subject, asset, and version. Each ContentVersion has
  a new UUID, so no upload can produce an existing key: immutability follows
  from the key structure. A whole Subject or asset can be listed or disposed
  of by prefix (NFR-SEC-014). Only one bucket policy and one service
  credential to manage.
- **Cons:** Access control is enforced by the backend, not by MinIO.
  Acceptable here, because clients never get MinIO credentials.

### B. One bucket per Subject
- **Pros:** Isolation per Subject at the storage level.
- **Cons:** The number of buckets grows with the catalogue. Bucket naming
  rules have to be mapped from Subject codes. Policies and credentials
  multiply. Teachers still never talk to MinIO directly, so the isolation
  adds nothing beyond backend RBAC.

### C. Content-addressed keys (`sha256/{hash}`), deduplicated
- **Pros:** Re-uploading the same file stores one copy.
- **Cons:** Several ContentVersions, possibly in different Subjects, would
  share one object. Disposal (NFR-SEC-014) would then need reference
  counting, and per-Subject prefixes are lost. 25 MB course files at
  one-college scale do not justify the extra complexity.

## Recommendation
**Option A**, with these rules:
1. **Bucket:** `uniadapt-content`, private, with no anonymous or public
   policy. The bucket name comes from configuration.
2. **Key:** `subjects/{subject_id}/assets/{content_asset_id}/versions/{content_version_id}/original.{ext}`,
   where `{ext}` comes from the **validated** type (pdf|pptx|docx|txt), not
   from the uploaded filename. The original filename is stored only in
   PostgreSQL. This keeps user-supplied text and personal data out of keys
   and avoids path-injection problems.
3. **Write once:** the backend writes each key exactly once, after
   validation, and never re-puts an existing key. ContentVersion stores the
   key, the SHA-256 of the file, its size, and the validated MIME type, so
   the file's integrity can be checked again later.
4. **Credentials:** the backend and celery use a dedicated MinIO access key
   whose policy allows only `uniadapt-content`, not the root credentials
   (NFR-SEC-013). Values come from `.env` and are never committed.
5. **Downloads:** files are served through backend endpoints that check
   assignment or enrollment scope, or through short-lived presigned GET URLs
   issued only after that check. The choice between the two is for the
   Phase 8 material viewer.
6. **Derived artifacts** (OCR page images, extracted text) are **not**
   stored in MinIO. Extracted and chunk text lives in PostgreSQL. Page
   images are regenerated when needed, because the pipeline is
   deterministic (ADR-0013 and ADR-0014).

Why:
1. Immutability comes from the key scheme (a new UUID per version) rather
   than from process discipline. This meets FR-CON-004 and NFR-DAT-002 with
   no extra MinIO features.
2. It matches the data model and the retention prefixes, so later phases
   (Phase 8 viewer, Phase 9 disposal) need no changes to the layout.
3. It meets NFR-SEC-013's least-privilege requirement with a single scoped
   credential.

## Consequences if accepted
- The Phase 2 plan adds a bucket-bootstrap step (create the bucket if it is
  missing, apply a private policy, create the scoped service key) and adds
  the MinIO settings to `app/core/config.py` and `.env.example`.
- The Python client library is a separate choice: the `minio` SDK or
  `boto3`. This ADR does not decide it. If not covered by another ADR, the
  plan must name it in Risks & Open Questions.
- MinIO bucket versioning or Object Lock is **not** required by this ADR.
  Object Lock retention would make NFR-SEC-014 disposal harder. If a human
  wants protection against accidental overwrite beyond write-once keys, a
  new ADR can add bucket versioning.
- Rollback (FR-CON-004) only moves the active pointer in PostgreSQL. No
  objects are copied or moved.
