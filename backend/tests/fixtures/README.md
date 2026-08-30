# Synthetic document corpus (T60)

Twenty documents across the six extractable types, rendered from the HTML
templates in `templates/` by `scripts/generate-documents.mjs`.

**Every figure, name, address and number here is invented.** National register
numbers use an obviously-fake `00.00.00-000.00` shape, employers and notaries
are made up, and no figure came from a real document. That is the point of the
corpus: extraction can be tested end to end without anyone's real payslip.

`expected.yaml` holds what each document should produce — the type, and the
fields a correct read returns. It is data, not schema, which is the one place
YAML genuinely belongs here (the schemas themselves are pydantic, T56).

## Regenerating

```bash
cd frontend && node ../backend/tests/fixtures/scripts/generate-documents.mjs
```

Playwright is already a dev dependency for the e2e suite, so rendering needs no
new tooling. The rendered files are committed so a test run never depends on a
browser being installed.

## The two tiers (T61)

* **Tier 1**, always in `make test`: `expected.yaml` drives the deterministic
  layer — evaluate(), field validation, and the mapping onto a proposal. No
  network, no key, no cost.
* **Tier 2**, opt-in: the rendered files actually go to the model.
  `RUN_LIVE_CLASSIFIER=1 pytest -m live`. Costs money and is not deterministic,
  so it is never a gate.

A synthetic `loonfiche` is cleaner than a photographed one, so Tier 2 passing
does not prove the model handles a crumpled phone photo. Stated here rather
than implied away.
