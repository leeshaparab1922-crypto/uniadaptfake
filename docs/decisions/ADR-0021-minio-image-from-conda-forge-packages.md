# ADR-0021: Build the MinIO image from checksum-pinned conda-forge packages

- **Status:** Proposed (awaiting human acceptance; implemented on branch `phase-2-ingestion-curriculum` so CI can run)
- **Date:** 2026-10-05
- **Affects:** `docker-compose.yml` (`minio`, `minio-init`), CI (`.github/workflows/backend-tests.yml`), every phase that stores files
- **Supersedes (once Accepted):** the "`minio/mc` Docker image" item of ADR-0019. ADR-0019's other items and ADR-0018's bucket layout stay as they are.
- **SRS refs:** Section 5.1 fixed stack (MinIO); Section 45; NFR-SEC-013

## Context
- The open-source MinIO project is archived upstream. `dl.min.io` returns `410 Gone` for the server and client binaries, with a notice that no security updates or advisories will follow.
- On 2026-10-05 the first CI run of PR #2 failed before any test ran: `pull access denied for minio/minio, repository does not exist`. `minio/minio`, `minio/mc`, `quay.io/minio/minio` and `quay.io/minio/mc` can no longer be pulled.
- `bitnami/minio` is gone. `bitnamilegacy/minio` still exists but is a frozen image (last updated 2025-08-19) under a legacy namespace.
- conda-forge publishes `minio-server 2025.10.15.17.29.55` and `minio-client 2025.08.13.08.35.41`, built from the last upstream releases. The Phase 2 verification ran against exactly these binaries, natively in WSL.
- The project owner accepted the MinIO-archived risk when shipping Phase 2 (2026-10-05) and asked for CI to be fixed.

## Decision
- `infra/minio/Dockerfile` builds `uniadapt/minio:2025.10.15`. It downloads the two conda-forge packages by exact version, checks each against its published SHA-256 (`5be30a90…068e` for the server, `5dc8fdb7…6c39` for `mc`), extracts `bin/minio` and `bin/mc` into `debian:bookworm-slim`, and runs as a non-root `minio` user.
- `docker-compose.yml` builds and uses that image for both `minio` and the one-shot `minio-init` bootstrap. The healthcheck uses MinIO's `/minio/health/ready` endpoint.

## Alternatives considered
- `bitnamilegacy/minio` and `bitnamilegacy/minio-client`: frozen images, with different entrypoints and configuration conventions from upstream, and no checksum-pinned source.
- Building MinIO from source in CI: a Go toolchain per build, slower, and the same upstream code.
- Replacing MinIO with another S3-compatible store: a fixed-stack change that needs an SRS amendment. Left for a separate decision.

## Consequences
- CI and local Compose no longer depend on removed images.
- The MinIO version is frozen at the last upstream release, so upstream security fixes will not arrive. The risk the owner accepted remains: a maintained replacement still needs its own decision, an SRS amendment and an ADR.
- Updating MinIO means changing the version and SHA-256 build arguments, deliberately.
