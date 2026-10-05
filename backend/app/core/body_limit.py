"""Request-body size cap applied before any route, dependency, or form parser runs.

FastAPI parses a multipart body (spooling it to disk) before the handler and its
auth/role/assignment dependencies execute, so a size check inside the handler
comes too late: a client sending a chunked body with no Content-Length could
make the server write an unbounded amount to disk first. This ASGI middleware
rejects an oversize body with 413 as soon as the declared Content-Length, or the
bytes actually received so far, exceed the cap (SRS Section 17 25 MB limit,
NFR-SEC-009, plan P-12). The per-file cap in the upload route still applies.

When the cap is crossed mid-stream, reading stops at once. FastAPI's form parser
turns that interruption into its own 400 response, so the middleware replaces
whatever response the app starts with the 413 (finding N1).
"""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class _BodyTooLarge(Exception):
    pass


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_body_bytes: int, limit_mb: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.limit_mb = limit_mb

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for name, value in scope.get("headers", []):
            if name == b"content-length":
                if value.isdigit() and int(value) > self.max_body_bytes:
                    await self._reject(send)
                    return
                break

        received = 0
        too_large = False
        rejected = False
        app_response_started = False

        async def limited_receive() -> Message:
            nonlocal received, too_large
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    too_large = True
                    raise _BodyTooLarge
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal rejected, app_response_started
            if too_large:
                # Replace the app's own error (e.g. FastAPI's 400 "error parsing the body").
                if not rejected:
                    rejected = True
                    await self._reject(send)
                return
            if message["type"] == "http.response.start":
                app_response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _BodyTooLarge:
            if app_response_started:
                raise
        if too_large and not rejected and not app_response_started:
            await self._reject(send)

    async def _reject(self, send: Send) -> None:
        body = json.dumps({"detail": f"File exceeds the {self.limit_mb} MB limit."}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
