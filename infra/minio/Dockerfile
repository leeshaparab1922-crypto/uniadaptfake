# MinIO server + mc client image for UniAdapt AI (ADR-0021).
#
# The official minio/minio and minio/mc images are no longer pullable (the open-source MinIO
# project is archived upstream). This image is built from the conda-forge packages of the last
# MinIO releases, the same binaries the Phase 2 verification ran against. Each package is
# downloaded by exact version and checked against its published SHA-256 before use.
FROM debian:bookworm-slim AS fetch

ARG MINIO_PKG_URL=https://api.anaconda.org/download/conda-forge/minio-server/2025.10.15.17.29.55/linux-64/minio-server-2025.10.15.17.29.55-hbcca054_0.conda
ARG MINIO_PKG_SHA256=5be30a904d2f5d5defa3be69c9f8fa519fde68f907049e351028727c90a5068e
ARG MC_PKG_URL=https://api.anaconda.org/download/conda-forge/minio-client/2025.08.13.08.35.41/linux-64/minio-client-2025.08.13.08.35.41-hfc2019e_0.conda
ARG MC_PKG_SHA256=5dc8fdb7306c97d7243328350cc43b44a7f4e1c08b3d0bf22df18d3adb476c39

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl unzip zstd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /pkg
# A .conda package is a zip holding pkg-*.tar.zst; the binary is bin/<name> inside it.
RUN set -eu; \
    curl -fsSL -o minio.conda "$MINIO_PKG_URL"; \
    echo "$MINIO_PKG_SHA256  minio.conda" | sha256sum -c -; \
    unzip -q minio.conda 'pkg-*.tar.zst' -d minio; \
    zstd -dc minio/pkg-*.tar.zst | tar -x -C /opt bin/minio; \
    curl -fsSL -o mc.conda "$MC_PKG_URL"; \
    echo "$MC_PKG_SHA256  mc.conda" | sha256sum -c -; \
    unzip -q mc.conda 'pkg-*.tar.zst' -d mc; \
    zstd -dc mc/pkg-*.tar.zst | tar -x -C /opt bin/mc; \
    /opt/bin/minio --version; \
    /opt/bin/mc --version

FROM debian:bookworm-slim

# curl is used by the compose healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --create-home --uid 1000 minio \
    && mkdir -p /data \
    && chown minio:minio /data

COPY --from=fetch /opt/bin/minio /usr/local/bin/minio
COPY --from=fetch /opt/bin/mc /usr/local/bin/mc

USER minio
VOLUME ["/data"]
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]
