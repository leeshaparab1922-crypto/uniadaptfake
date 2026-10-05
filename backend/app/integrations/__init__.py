"""Adapters to external systems (MinIO, Tesseract, HuggingFace embeddings).

Domain/deterministic services depend only on the Protocols in
`app.services.ingestion.ports`, never on these concrete classes.
"""
