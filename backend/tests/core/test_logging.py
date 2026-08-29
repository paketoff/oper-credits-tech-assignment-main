"""Every line is JSON, carries a request id, and carries no payload.

DEP-029 - DEP-031, DEP-035, DEP-049. In mortgage origination the payload is the
sensitive data and telemetry is where it leaks, so these are not hygiene tests.
"""

import json
import logging

import pytest
import structlog

from app.core.logging import REQUEST_ID_HEADER, configure, redact


@pytest.fixture(autouse=True)
def _configured():
    configure()
    structlog.contextvars.clear_contextvars()


def _emit(caplog, **fields) -> dict[str, object]:
    # structlog renders through the stdlib logger, so the JSON line arrives as
    # the record's message rather than on stdout directly.
    caplog.set_level(logging.INFO)
    structlog.get_logger().info("event", **fields)
    return json.loads(caplog.messages[-1])


def test_log_line_is_json_with_request_id(caplog):
    structlog.contextvars.bind_contextvars(request_id="abc-123")

    line = _emit(caplog, detail="anything")

    assert line["request_id"] == "abc-123"
    assert line["event"] == "event"
    assert line["level"] == "info"


async def test_response_carries_request_id_header(client):
    response = await client.get("/health")

    assert response.headers[REQUEST_ID_HEADER]


async def test_an_inbound_request_id_is_honoured(client):
    # A trace has to survive a proxy, so an id we are given is reused rather
    # than replaced.
    response = await client.get("/health", headers={REQUEST_ID_HEADER: "from-upstream"})

    assert response.headers[REQUEST_ID_HEADER] == "from-upstream"


def test_email_is_redacted_from_log_output(caplog):
    line = _emit(caplog, email="jan@example.com")

    assert line["email"] == "[redacted]"
    assert "jan@example.com" not in json.dumps(line)


def test_amount_is_redacted_from_log_output(caplog):
    # Substring, not exact match: the field is rarely called "amount". It is
    # called loan_amount, monthly_net_income, property_value.
    line = _emit(
        caplog,
        loan_amount="270000.00",
        monthly_net_income="3200.00",
        property_value="300000.00",
    )

    rendered = json.dumps(line)
    assert "270000.00" not in rendered
    assert "3200.00" not in rendered
    assert "300000.00" not in rendered


@pytest.mark.parametrize(
    "key",
    ["password", "token", "secret", "api_key", "authorization", "full_name", "filename"],
)
def test_every_denylisted_key_is_redacted(key):
    assert redact(None, "", {key: "sensitive"})[key] == "[redacted]"


def test_redaction_keeps_the_key(caplog):
    # The key survives so a line still shows the field was present. A log that
    # drops the key entirely is harder to debug and no more private.
    line = _emit(caplog, email="jan@example.com")

    assert "email" in line


def test_an_innocent_field_is_left_alone(caplog):
    line = _emit(caplog, region="FLANDERS", doc_type="PAYSLIPS", size_bucket="small")

    assert line["region"] == "FLANDERS"
    assert line["doc_type"] == "PAYSLIPS"
    assert line["size_bucket"] == "small"
