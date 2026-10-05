# UniAdapt AI backend/celery image (Phase 2 slice 2A).
# - Tesseract 5 + English data (ADR-0013), pinned to the Debian bookworm package versions
#   (source packages tesseract 5.3.0-2 and tesseract-lang 1:4.1.0-2). If Debian replaces either
#   version, the build fails instead of silently changing OCR output; update the pins on purpose.
#   The running version is also recorded in every OCR stage record.
# - CPU-only PyTorch + sentence-transformers for local BAAI/bge-m3 inference (ADR-0015).
FROM python:3.11-slim-bookworm

ARG TESSERACT_VERSION=5.3.0-2
ARG TESSERACT_ENG_VERSION=1:4.1.0-2
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/hf-cache

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        "tesseract-ocr=${TESSERACT_VERSION}" \
        "tesseract-ocr-eng=${TESSERACT_ENG_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install ".[embeddings]"

COPY . .
VOLUME ["/hf-cache"]
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
