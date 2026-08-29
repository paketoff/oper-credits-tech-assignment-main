"""One error shape, one mapping, and no leaking. VAL-004 - VAL-007, API-013 - API-015."""

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from app.core import exception_handlers
from app.core.errors import MESSAGES, DomainError, SimulationError
from app.core.exception_handlers import STATUSES


@pytest.fixture
def failing_app() -> FastAPI:
    """An app whose only routes fail, so the handlers are what is under test."""
    application = FastAPI()
    exception_handlers.register(application)

    @application.get("/boom")
    async def boom() -> JSONResponse:
        raise SimulationError(code="LOAN_AMOUNT_NOT_POSITIVE", field="own_contribution")

    @application.get("/leaky")
    async def leaky() -> JSONResponse:
        raise SimulationError(
            code="JKP_COMPUTATION_FAILED",
            detail="/Users/someone/secret/path/app.db",
        )

    @application.get("/typed")
    async def typed(term_months: int) -> JSONResponse:
        return JSONResponse({"term_months": term_months})

    return application


@pytest.fixture
async def failing_client(failing_app):
    transport = ASGITransport(app=failing_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_domain_error_renders_expected_shape(failing_client):
    response = await failing_client.get("/boom")

    assert response.status_code == 422
    assert response.json() == {
        "code": "LOAN_AMOUNT_NOT_POSITIVE",
        "message": MESSAGES["LOAN_AMOUNT_NOT_POSITIVE"],
        "field": "own_contribution",
    }


async def test_pydantic_error_normalised_to_same_shape(failing_client):
    # API-015: a raw FastAPI `detail` array never reaches the client. It has a
    # different shape per error type, and the frontend would need a second
    # error format to place a message beside a field.
    response = await failing_client.get("/typed?term_months=not-a-number")

    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "message": MESSAGES["VALIDATION_ERROR"],
        "field": "term_months",
    }
    assert "detail" not in response.json()


def test_every_declared_code_maps_to_a_status():
    # CQ-063 closed mechanically: the registry and the mapping cannot drift,
    # because this fails the moment one gains a code the other has not.
    assert set(MESSAGES) == set(STATUSES)


@pytest.mark.parametrize("code", sorted(MESSAGES))
def test_every_status_is_a_plausible_http_error(code):
    assert 400 <= STATUSES[code] <= 599


async def test_error_response_contains_no_stack_trace(failing_client):
    # CQ-062, VAL-030. `detail` exists for the log and must not be rendered:
    # here it holds a filesystem path, which is exactly what must not escape.
    response = await failing_client.get("/leaky")
    body = response.text

    assert response.status_code == 500
    assert "/Users/" not in body
    assert "Traceback" not in body
    assert "app.db" not in body


def test_domain_error_rejects_a_code_outside_the_registry():
    # A code that is not in the registry does not exist (CQ-063). Raising one
    # should fail here, loudly, rather than reach a client as an empty message.
    with pytest.raises(KeyError):
        DomainError(code="INVENTED_CODE")
