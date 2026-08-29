"""Rejects an oversized request body before a handler sees it (VAL-024).

Raw ASGI rather than a Starlette `BaseHTTPMiddleware`, deliberately. The point
of this rule is that a 100 MB upload is refused **before** the bytes are
buffered into memory, and `BaseHTTPMiddleware` reads the body to hand it on —
which is the failure it exists to prevent.

Neither Starlette nor uvicorn has a maximum-body-size setting. The spec used to
say the limit was "enforced at the ASGI layer", which names no switch that
exists; an implementer following it would either hunt for a flag or fall back to
reading the body and checking its length afterwards.
"""

from dataclasses import dataclass

from starlette.requests import ClientDisconnect
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import MESSAGES

MAX_BODY_BYTES = 10 * 1024 * 1024  # DOC-002, VAL-013

_CODE = "DOCUMENT_TOO_LARGE"
_STATUS = 413


@dataclass(slots=True)
class _Overrun:
    """Whether this request went over, and whether we have already answered."""

    received: int = 0
    exceeded: bool = False
    answered: bool = False


class BodySizeLimitMiddleware:
    """Refuses a request whose body exceeds the limit.

    Two checks, because one is not enough. `Content-Length` catches the honest
    client cheaply and before a single byte of body arrives. A chunked upload
    sends no such header, so the receive channel is wrapped in a counter that
    aborts the moment the running total passes the limit.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        """Wrap an application.

        Args:
            app: The next application in the ASGI chain.
            max_bytes: The largest body accepted, in bytes.
        """
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Apply the limit to HTTP requests, and pass everything else through."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        if self._declared_length(scope) > self._max_bytes:
            await _send_too_large(send)
            return
        await self._guarded(scope, receive, send)

    def _declared_length(self, scope: Scope) -> int:
        """Read Content-Length, treating an absent or unparseable one as zero.

        Zero rather than a rejection: a request with no such header is not
        oversized, it is unmeasured, and the counter below is what measures it.
        """
        headers: dict[bytes, bytes] = dict(scope.get("headers", []))
        raw = headers.get(b"content-length")
        if raw is None:
            return 0
        try:
            return int(raw)
        except ValueError:
            return 0

    async def _guarded(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Run the app with both channels watched.

        Both have to be wrapped, not just `receive`. Cutting the request stream
        short makes the handler raise `ClientDisconnect`, which would surface to
        the client as a 500 — a body that is too large is a 413, and the client
        should be told which of the two happened.
        """
        state = _Overrun()

        async def counted() -> Message:
            message = await receive()
            if message["type"] == "http.request":
                state.received += len(message.get("body", b""))
                if state.received > self._max_bytes:
                    state.exceeded = True
                    # Do not pass the chunk on: the handler never sees a body it
                    # should not have been given.
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Message) -> None:
            if not state.exceeded:
                await send(message)
                return
            if not state.answered:
                state.answered = True
                await _send_too_large(send)

        try:
            await self._app(scope, counted, guarded_send)
        except ClientDisconnect:
            if not state.exceeded:
                raise
            if not state.answered:
                state.answered = True
                await _send_too_large(send)


async def _send_too_large(send: Send) -> None:
    """Answer with the shared error shape, without going through a handler.

    This runs above the exception handlers, so the body is built here rather
    than raised. It still uses the registry message, so there is one text for
    this code and not two (CQ-063).
    """
    body = f'{{"code":"{_CODE}","message":"{MESSAGES[_CODE]}","field":"file"}}'.encode()
    await send(
        {
            "type": "http.response.start",
            "status": _STATUS,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
