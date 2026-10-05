"""Finding M4: oversize request bodies are rejected before routing, auth, or form parsing."""

from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.testclient import TestClient

from app.core.body_limit import BodySizeLimitMiddleware

LIMIT = 100


def _client() -> tuple[TestClient, list[str]]:
    reached: list[str] = []
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=LIMIT, limit_mb=25)

    @app.post("/echo")
    async def echo(request: Request) -> dict[str, int]:
        reached.append("handler")
        return {"size": len(await request.body())}

    return TestClient(app), reached


def test_body_within_limit_reaches_the_handler():
    client, reached = _client()
    resp = client.post("/echo", content=b"x" * LIMIT)
    assert resp.status_code == 200 and resp.json() == {"size": LIMIT}
    assert reached == ["handler"]


def test_declared_oversize_body_is_rejected_before_the_handler():
    client, reached = _client()
    resp = client.post("/echo", content=b"x" * (LIMIT + 1))
    assert resp.status_code == 413
    assert resp.json() == {"detail": "File exceeds the 25 MB limit."}
    assert reached == []


def test_chunked_body_without_content_length_is_capped_while_streaming():
    client, _ = _client()

    def chunks():
        for _ in range(10):
            yield b"y" * 50

    resp = client.post("/echo", content=chunks())
    assert resp.status_code == 413


def test_get_requests_pass_through():
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=LIMIT, limit_mb=25)

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"ok": "yes"}

    assert TestClient(app).get("/ping").json() == {"ok": "yes"}


def test_app_applies_the_cap_with_cors_outermost():
    from app.main import MULTIPART_OVERHEAD_BYTES, create_app

    app = create_app()
    names = [m.cls.__name__ for m in app.user_middleware]
    assert names.index("CORSMiddleware") < names.index("BodySizeLimitMiddleware")
    limit = next(m for m in app.user_middleware if m.cls is BodySizeLimitMiddleware)
    assert limit.kwargs["max_body_bytes"] == 25 * 1024 * 1024 + MULTIPART_OVERHEAD_BYTES


def _multipart(size: int) -> bytes:
    head = (
        b'--B\r\nContent-Disposition: form-data; name="file"; filename="a.txt"\r\n'
        b"Content-Type: text/plain\r\n\r\n"
    )
    return head + b"x" * size + b"\r\n--B--\r\n"


def _upload_client() -> TestClient:
    # Module-level imports: with postponed annotations FastAPI resolves them from globals.
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=1000, limit_mb=25)

    @app.post("/upload")
    def upload(file: Annotated[UploadFile, File()]) -> dict[str, str]:
        return {"name": file.filename or ""}

    return TestClient(app)


def test_chunked_multipart_upload_over_the_cap_gets_413_not_a_parse_error():
    """Finding N1: FastAPI's form parser turns the interrupted read into its own 400; the
    middleware must replace it with the 413."""
    body = _multipart(5000)

    def chunks():
        for i in range(0, len(body), 500):
            yield body[i : i + 500]

    resp = _upload_client().post(
        "/upload", content=chunks(), headers={"content-type": "multipart/form-data; boundary=B"}
    )
    assert resp.status_code == 413
    assert resp.json() == {"detail": "File exceeds the 25 MB limit."}


def test_declared_oversize_multipart_upload_gets_413():
    resp = _upload_client().post(
        "/upload", content=_multipart(5000), headers={"content-type": "multipart/form-data; boundary=B"}
    )
    assert resp.status_code == 413


def test_multipart_upload_within_the_cap_succeeds():
    resp = _upload_client().post(
        "/upload", content=_multipart(100), headers={"content-type": "multipart/form-data; boundary=B"}
    )
    assert resp.status_code == 200 and resp.json() == {"name": "a.txt"}
