"""The Anthropic call: renders page one and returns a structured verdict.

Two failure modes, kept deliberately apart:

* **A malformed answer is not a failure.** Invalid JSON, a category outside the
  enum, a confidence of 2.0, an empty body — all degrade to `UNKNOWN` at
  confidence 0 (AI-011), which `evaluator.py` then bands as `INCONCLUSIVE`.
  The borrower is told nothing, which is the correct outcome for an answer we
  cannot read.
* **A transport failure is.** A timeout, a network error, a 4xx — these raise
  `ClassificationError`, and the pipeline (T37) turns that into `FAILED` and
  stops. `FAILED` renders as nothing (AI-021): a failed classification is our
  problem, not the borrower's.

`ClassificationError` is a plain exception, deliberately **not** a
`DomainError`: domain errors carry a registry code and map to an HTTP status
(CQ-053), and this one must never reach the borrower at all (AI-005, AI-023).
"""

import json
from io import BytesIO
from typing import Final

import anthropic
from PIL import Image
from pydantic import BaseModel, ValidationError

from app.core.enums import DocumentType
from app.domains.documents.classification.entities import (
    ClassificationVerdict,
    ClassifiedType,
)
from app.domains.documents.classification.prompts import EXTRACTION_PROMPT, SYSTEM_PROMPT
from app.domains.documents.extraction.schemas import schema_for

# AI-013. Model and cap are named constants so the tuning surface is one place.
# Sonnet is enough while the response is four fields; `9-ai-classification.md`
# Appendix B records why it is not an older tier.
# T57 supersedes AI-013's choice. Sonnet at 300 tokens was reasoned for a
# four-field classification; this same call now also reads numbers off the page,
# and the hard part stopped being "is this a payslip" and became "is that
# 3.200 or 3.020". Latency is free here — the call runs in a background task
# after the 201 (AI-018) — and the volume is a handful per application, so the
# cost difference is rounding error against a misread figure the borrower then
# has to correct by hand.
#
# Both are one-line constants precisely so this can go back to Sonnet once
# T61's Tier 2 measures whether the difference is real.
MODEL: Final = "claude-opus-5"
MAX_TOKENS: Final = 1500

# AI-022. One retry on a network error, none on a 4xx — anthropic's client
# distinguishes the two, so this does not need hand-rolling.
TIMEOUT_SECONDS: Final = 10.0
MAX_RETRIES: Final = 1

# AI-007. One page, at most 1500px on the long edge. Enough to identify a
# document type, and it keeps the call cheap and fast.
MAX_EDGE_PX: Final = 1500
RENDER_DPI: Final = 150

_PDF_CONTENT_TYPE: Final = "application/pdf"
_PNG_MEDIA_TYPE: Final = "image/png"

# AI-011. The one verdict a caller gets when the answer cannot be read.
_UNREADABLE = ClassificationVerdict(
    doc_type=ClassifiedType.UNKNOWN, confidence=0.0, reason="unreadable response"
)


class ClassificationError(Exception):
    """The classifier could not be reached or did not answer in time."""


def _downscale(image: Image.Image) -> Image.Image:
    """Fit the image inside MAX_EDGE_PX without changing its aspect ratio."""
    longest = max(image.width, image.height)
    if longest <= MAX_EDGE_PX:
        return image
    scale = MAX_EDGE_PX / longest
    return image.resize((int(image.width * scale), int(image.height * scale)))


def render_first_page(content: bytes, content_type: str) -> bytes:
    """Render page one of an upload to PNG bytes (AI-007, AI-008).

    Args:
        content: The whole uploaded file. Only its first page is ever used, and
            nothing past it is sent anywhere (AI-009).
        content_type: The type the upload was accepted as, decided by magic
            bytes rather than by the client (VAL-022).

    Returns:
        PNG bytes, at most `MAX_EDGE_PX` on the long edge.

    Raises:
        ClassificationError: The bytes could not be rendered at all. Treated as
            a failure rather than an `UNKNOWN` verdict, because nothing was
            ever asked — there is no answer to disbelieve.
    """
    try:
        if content_type == _PDF_CONTENT_TYPE:
            from pdf2image import convert_from_bytes

            pages = convert_from_bytes(
                content, dpi=RENDER_DPI, first_page=1, last_page=1
            )
            image = pages[0]
        else:
            image = Image.open(BytesIO(content))
        buffer = BytesIO()
        _downscale(image.convert("RGB")).save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception as exc:
        raise ClassificationError("could not render the first page") from exc


def _system_prompt(schema: type[BaseModel] | None) -> str:
    """The base prompt, plus the fields to extract when there are any.

    The schema is generated from the pydantic model (`model_json_schema()`), so
    the prompt and the type it parses into cannot drift apart — adding a field
    changes both at once.
    """
    if schema is None:
        return SYSTEM_PROMPT
    return EXTRACTION_PROMPT.format(schema=json.dumps(schema.model_json_schema()))


def _parse(
    text: str, schema: type[BaseModel] | None
) -> tuple[ClassificationVerdict, object | None]:
    """Turn the model's reply into a verdict, or into `UNKNOWN` at 0 (AI-011).

    Every unhappy path lands in the same place on purpose. A category the enum
    does not have, a confidence outside 0..1, a missing key, prose instead of
    JSON — none of them are distinguishable in usefulness, and all of them mean
    the same thing to the borrower: nothing is shown.
    """
    try:
        payload = json.loads(text)
        doc_type = ClassifiedType(payload["doc_type"])
        confidence = float(payload["confidence"])
        if not 0.0 <= confidence <= 1.0:
            return _UNREADABLE, None
        verdict = ClassificationVerdict(
            doc_type=doc_type, confidence=confidence, reason=str(payload.get("reason", ""))[:120]
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return _UNREADABLE, None
    return verdict, _parse_fields(payload.get("fields"), schema)


def _parse_fields(raw: object, schema: type[BaseModel] | None) -> object | None:
    """Validate the extracted block, or give up quietly.

    Unparseable fields are **not** an unreadable verdict: the type may still
    have been identified correctly. The document is classified as usual and
    simply proposes nothing, which is the same outcome as a document we do not
    extract from at all.
    """
    if schema is None or not isinstance(raw, dict):
        return None
    try:
        return schema.model_validate(raw)
    except ValidationError:
        return None


class ClassificationClient:
    """Sends one rendered page to the model and returns what it answered.

    The request carries **the image and nothing else** (AI-009): no filename,
    no application, borrower or account data, and nothing past page one. The
    filename in particular is withheld on purpose — it is borrower-controlled,
    often contains a real name, and would let the model classify from the name
    rather than the content, which is exactly the shortcut that makes the
    feature useless.
    """

    def __init__(self, api_key: str) -> None:
        """Build the client. Only ever constructed when the flag is on (AI-024)."""
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key, timeout=TIMEOUT_SECONDS, max_retries=MAX_RETRIES
        )

    async def classify(
        self, page_png: bytes, claimed: DocumentType | None = None
    ) -> tuple[ClassificationVerdict, object | None]:
        """Ask what the page is and, if it is what was claimed, what it says.

        **One call, not two** (T57). The claimed type is known at upload time,
        so the request asks both questions at once: what is this actually, and
        — if it is a payslip — what are its fields. No discriminated union and
        no second round trip, because the schema is chosen from what the
        borrower already told us.

        Args:
            page_png: One rendered page, from `render_first_page`.
            claimed: What the borrower declared. When it has an extraction
                schema, the model is also asked to fill it in.

        Returns:
            The verdict, and the parsed fields or None. **The caller must
            discard the fields unless `evaluate()` returns `CONFIRMED`** —
            fields read off a document that turned out to be something else
            describe the wrong document.

        Raises:
            ClassificationError: The call failed or timed out. Never surfaced
                to the borrower — the pipeline records `FAILED` and stops
                (AI-005, AI-023).
        """
        schema = schema_for(claimed) if claimed is not None else None
        try:
            message = await self._client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=_system_prompt(schema),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": _PNG_MEDIA_TYPE,
                                    "data": _b64(page_png),
                                },
                            }
                        ],
                    }
                ],
            )
        except Exception as exc:
            raise ClassificationError("the classifier could not be reached") from exc
        return _parse(_first_text(message), schema)


def _b64(data: bytes) -> str:
    """Base64 for the image block."""
    import base64

    return base64.standard_b64encode(data).decode("ascii")


def _first_text(message: object) -> str:
    """Pull the first text block out of a response, tolerating any other shape.

    Defensive rather than trusting: an unexpected response shape degrades to
    `UNKNOWN` through `_parse` instead of raising, because a shape we did not
    expect is an answer we cannot read, not a transport failure.
    """
    content = getattr(message, "content", None)
    if not content:
        return ""
    text = getattr(content[0], "text", None)
    return text if isinstance(text, str) else ""
