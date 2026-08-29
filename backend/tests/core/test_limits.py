"""An oversized body is refused before a handler sees it. VAL-024, API-051.

The point of these tests is *when* the rejection happens, not that it happens.
A check that reads the body first and measures it afterwards would pass a naive
assertion about the status code while doing the one thing the rule forbids.
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from app.core.errors import MESSAGES
from app.core.limits import BodySizeLimitMiddleware

_LIMIT = 1024


@pytest.fixture
def guarded_app() -> FastAPI:
    application = FastAPI()
    application.add_middleware(BodySizeLimitMiddleware, max_bytes=_LIMIT)
    # Records how much body the handler was actually given, so a test can tell
    # "rejected before buffering" from "rejected after".
    application.state.bytes_seen = None

    @application.post("/upload")
    async def upload(request: Request) -> JSONResponse:
        body = await request.body()
        application.state.bytes_seen = len(body)
        return JSONResponse({"received": len(body)})

    return application


@pytest.fixture
async def guarded_client(guarded_app):
    transport = ASGITransport(app=guarded_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_a_body_within_the_limit_is_passed_through(guarded_client):
    response = await guarded_client.post("/upload", content=b"x" * 100)

    assert response.status_code == 200
    assert response.json() == {"received": 100}


async def test_oversized_body_is_rejected_with_the_shared_error_shape(guarded_client):
    response = await guarded_client.post("/upload", content=b"x" * (_LIMIT + 1))

    assert response.status_code == 413
    assert response.json() == {
        "code": "DOCUMENT_TOO_LARGE",
        "message": MESSAGES["DOCUMENT_TOO_LARGE"],
        "field": "file",
    }


async def test_oversized_body_never_reaches_the_handler(guarded_app, guarded_client):
    # This is the assertion that matters. Content-Length is checked before a
    # single byte of body is read, so the handler is never entered at all.
    await guarded_client.post("/upload", content=b"x" * (_LIMIT + 1))

    assert guarded_app.state.bytes_seen is None


async def test_chunked_upload_without_content_length_is_still_capped(guarded_app, guarded_client):
    # A chunked request declares no length, so the header check cannot help and
    # the counter on the receive channel is what stops it.
    async def oversized_chunks():
        for _ in range(4):
            yield b"y" * 512

    response = await guarded_client.post("/upload", content=oversized_chunks())

    assert response.status_code != 200
    assert guarded_app.state.bytes_seen != 2048


async def test_a_lying_content_length_does_not_get_through(guarded_client):
    # A header claiming to be small does not buy a large body: the counter
    # measures what actually arrives.
    async def chunks():
        yield b"z" * (_LIMIT * 2)

    response = await guarded_client.post(
        "/upload",
        content=chunks(),
        headers={"content-length": "10"},
    )

    assert response.status_code != 200
