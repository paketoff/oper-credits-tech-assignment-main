"""The synthetic corpus, in two tiers. T60, T61.

**Tier 1 — always runs, no network, no key, no cost.** `expected.yaml` is the
answer key, and this tier proves our *deterministic* half against it: that the
fields validate against the schema they claim, and that the mapping onto a
financial proposal is right. It never asks a model anything.

**Tier 2 — opt-in, real API, never a gate.** `RUN_LIVE_CLASSIFIER=1 pytest -m
live` sends the rendered documents to the model and checks it identifies the
type and lands the numbers. It costs money and is not deterministic, so making
it a gate would buy flakiness and a bill at the same time.

A synthetic `loonfiche` is cleaner than a photographed one, so Tier 2 passing
does not prove the model handles a crumpled phone photo. Stated rather than
implied away.
"""

import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.core.enums import DocumentType
from app.domains.documents.extraction.proposal import to_proposal
from app.domains.documents.extraction.schemas import schema_for

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
_DOCUMENTS = _FIXTURES / "documents"
_CASES: list[dict[str, Any]] = yaml.safe_load(
    (_FIXTURES / "expected.yaml").read_text()
)["documents"]


def _ids(case: dict[str, Any]) -> str:
    return str(case["id"])


class TestCorpus:
    """Tier 1: the answer key against our own deterministic layer."""

    def test_the_corpus_covers_every_extractable_type(self) -> None:
        covered = {case["doc_type"] for case in _CASES}
        extractable = {
            doc_type.value for doc_type in DocumentType if schema_for(doc_type) is not None
        }
        assert covered == extractable

    @pytest.mark.parametrize("case", _CASES, ids=_ids)
    def test_every_case_has_both_rendered_formats(self, case: dict[str, Any]) -> None:
        """Committed, so a test run never depends on a browser being installed."""
        assert (_DOCUMENTS / f"{case['id']}.pdf").is_file()
        assert (_DOCUMENTS / f"{case['id']}.png").is_file()

    @pytest.mark.parametrize("case", _CASES, ids=_ids)
    def test_expected_fields_validate_against_their_schema(self, case: dict[str, Any]) -> None:
        """The answer key cannot claim a field the schema does not have (extra="forbid")."""
        schema = schema_for(DocumentType(case["doc_type"]))
        assert schema is not None

        assert schema.model_validate(case["fields"])

    @pytest.mark.parametrize("case", _CASES, ids=_ids)
    def test_expected_fields_map_to_the_expected_proposal(self, case: dict[str, Any]) -> None:
        """The mapping from a document to two numbers, checked case by case."""
        doc_type = DocumentType(case["doc_type"])
        schema = schema_for(doc_type)
        assert schema is not None
        proposal = to_proposal(doc_type, schema.model_validate(case["fields"]))
        expected = case["proposes"]

        if not expected:
            assert proposal is None or proposal.is_empty()
            return
        assert proposal is not None
        for field, value in expected.items():
            assert getattr(proposal, field) == Decimal(value)


@pytest.mark.live
@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_CLASSIFIER"),
    reason="Tier 2 costs money and is non-deterministic: set RUN_LIVE_CLASSIFIER=1 to run it.",
)
class TestLiveClassifier:
    """Tier 2: the same documents, actually sent to the model.

    Never part of `make test`. What it measures is whether the model earns the
    Opus-over-Sonnet choice recorded in `client.py` — swap the constant, run
    this, compare.
    """

    @pytest.mark.parametrize("case", _CASES, ids=_ids)
    async def test_the_model_identifies_the_type_and_lands_the_numbers(
        self, case: dict[str, Any]
    ) -> None:
        from app.core.config import get_settings
        from app.domains.documents.classification.client import (
            ClassificationClient,
            render_first_page,
        )

        claimed = DocumentType(case["doc_type"])
        content = (_DOCUMENTS / f"{case['id']}.png").read_bytes()
        client = ClassificationClient(get_settings().anthropic_api_key)

        verdict, fields = await client.classify(render_first_page(content, "image/png"), claimed)

        assert verdict.doc_type.value == case["doc_type"]
        for field, expected in case["fields"].items():
            actual = getattr(fields, field, None)
            if isinstance(expected, str) and expected.replace(".", "").isdigit():
                assert actual == Decimal(expected), field
