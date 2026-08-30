"""The classifier client. AI-007 - AI-013, AI-022, AI-035.

Entirely mocked: no key, no network, no cost. The two behaviours worth pinning
are the ones that are easy to get subtly wrong —

* a **malformed answer** is not a failure, it degrades to `UNKNOWN` at 0
  (AI-011), so the borrower is told nothing rather than told nonsense;
* the request carries **the image and nothing else** (AI-009), and in
  particular never the filename, which is borrower-controlled and would let the
  model classify from the name instead of the content.
"""

from io import BytesIO
from typing import Any

import pytest
from PIL import Image

from app.domains.documents.classification.client import (
    MAX_EDGE_PX,
    ClassificationClient,
    ClassificationError,
    render_first_page,
)
from app.domains.documents.classification.entities import ClassifiedType


class _Block:
    def __init__(self, text: str) -> None:
        self.text = text


class _Message:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]


class _FakeMessages:
    """Records the request and replays a canned answer."""

    def __init__(self, reply: str | Exception) -> None:
        self._reply = reply
        self.last_kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> _Message:
        self.last_kwargs = kwargs
        if isinstance(self._reply, Exception):
            raise self._reply
        return _Message(self._reply)


def _client(reply: str | Exception) -> tuple[ClassificationClient, _FakeMessages]:
    client = ClassificationClient(api_key="test-key-not-real")
    messages = _FakeMessages(reply)
    # The constructor builds a real AsyncAnthropic, but nothing is ever sent:
    # its messages resource is replaced before any call.
    client._client.messages = messages  # type: ignore[assignment]
    return client, messages


def _png(width: int, height: int) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="PNG")
    return buffer.getvalue()


async def test_a_well_formed_answer_becomes_a_verdict() -> None:
    client, _ = _client('{"doc_type": "PAYSLIPS", "confidence": 0.91, "reason": "a salary slip"}')

    verdict, _ = await client.classify(_png(10, 10))

    assert verdict.doc_type is ClassifiedType.PAYSLIPS
    assert verdict.confidence == 0.91


@pytest.mark.parametrize(
    "reply",
    [
        pytest.param("not json at all", id="prose_instead_of_json"),
        pytest.param("", id="empty_body"),
        pytest.param('{"doc_type": "PAYSLIP_TYPO", "confidence": 0.9}', id="unknown_category"),
        pytest.param('{"doc_type": "PAYSLIPS", "confidence": 2.0}', id="confidence_above_one"),
        pytest.param('{"doc_type": "PAYSLIPS", "confidence": -0.5}', id="negative_confidence"),
        pytest.param('{"confidence": 0.9}', id="missing_doc_type"),
        pytest.param(
            '{"doc_type": "PAYSLIPS", "confidence": "high"}', id="confidence_not_a_number"
        ),
        pytest.param("[]", id="json_but_not_an_object"),
    ],
)
async def test_malformed_json_degrades_to_unknown_zero_confidence(reply: str) -> None:
    """AI-011, AI-035. Every unreadable answer means the same thing to the borrower."""
    client, _ = _client(reply)

    verdict, _ = await client.classify(_png(10, 10))

    assert verdict.doc_type is ClassifiedType.UNKNOWN
    assert verdict.confidence == 0.0


async def test_filename_is_never_included_in_the_request() -> None:
    """AI-009. The one field whose absence is the point of the feature."""
    client, messages = _client('{"doc_type": "EPC", "confidence": 0.8}')

    await client.classify(_png(10, 10))

    sent = repr(messages.last_kwargs)
    assert "loonfiche-jan-janssens.pdf" not in sent
    # The user turn carries exactly one block, and it is the image.
    content = messages.last_kwargs["messages"][0]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "image"


async def test_a_transport_failure_raises_rather_than_degrading() -> None:
    """AI-022, AI-023. A failure to ask is not an answer to disbelieve."""
    client, _ = _client(TimeoutError("timed out"))

    with pytest.raises(ClassificationError):
        await client.classify(_png(10, 10))


async def test_the_model_and_cap_are_sent_as_configured() -> None:
    """T57 supersedes AI-013: the same call now also reads numbers off the page."""
    client, messages = _client('{"doc_type": "EPC", "confidence": 0.8}')

    await client.classify(_png(10, 10))

    assert messages.last_kwargs["model"] == "claude-opus-5"
    assert messages.last_kwargs["max_tokens"] == 1500


def test_only_first_page_is_rendered_and_downscaled() -> None:
    """AI-007. At most 1500px on the long edge, aspect ratio kept."""
    rendered = render_first_page(_png(3000, 1500), "image/png")

    image = Image.open(BytesIO(rendered))
    assert max(image.size) == MAX_EDGE_PX
    assert image.size == (MAX_EDGE_PX, MAX_EDGE_PX // 2)


def test_a_small_image_is_not_upscaled() -> None:
    rendered = render_first_page(_png(200, 100), "image/png")

    assert Image.open(BytesIO(rendered)).size == (200, 100)


def test_unrenderable_bytes_raise_rather_than_returning_a_verdict() -> None:
    """Nothing was asked, so there is no answer to disbelieve — this is a failure."""
    with pytest.raises(ClassificationError):
        render_first_page(b"not an image", "image/png")
