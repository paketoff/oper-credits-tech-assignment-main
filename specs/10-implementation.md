---
id: T
title: Implementation Plan
status: draft
version: 1.0.0
owner: paketoff
updated: 2026-08-29
---

# 10 — Implementation Plan

The order of work, broken into tickets. Read [`2-architecture.md`](2-architecture.md) first for the
ownership boundaries this plan depends on (ARC-028, ARC-029).

**This is the one document in `specs/` that is a plan, not a contract.** Specs 0 – 9 describe what
the system does; this one describes the order in which it gets built. Ticket ids `T01` – `T44` are
the identifiers — they go in commit messages, and there is no second numbering on top of them.

## Principles

**T-P1. Every ticket has a machine-verifiable done condition.** Not "implement the calculator" but
"this command exits zero with these test names passing". A ticket whose completion is a matter of
opinion cannot be handed to an agent, cannot be run in parallel, and cannot be reviewed quickly.

This is why the specs were written before any code. The spec defines the contract, the acceptance
criteria are the tests, and the agent has a condition it can check for itself.

**T-P2. Agents parallelise along file boundaries, not along tasks.** Two agents editing the same file
produce a merge problem no prompting fixes. The ownership table in `2-architecture.md` ARC-028 is the
concurrency plan; every ticket names the files it owns and may touch no others.

**T-P3. Tests are named up front.** Each ticket lists the test function names it must produce. An
agent given a list of test names has an unambiguous target; an agent told to "add tests" writes
filler.

## Ticket format

```
ID     | Title
Owner  | A domain core / B API / C frontend / D platform / you
Deps   | tickets that must be complete first
Files  | files this ticket may edit, and no others
Output | what must exist when it is done: functions, endpoints, artefacts
Tests  | the exact test function names to produce
Done   | a command that exits zero, or an observable fact
```

## Coverage policy

**T-P4. No global coverage threshold.** The brief is explicit: a few meaningful tests beat a sea of
generated ones. A percentage target produces tests on getters, which is the exact failure they are
warning against.

Two tiers instead:

**T-P5. Tier 1 — pure domain logic: 100%, enforced.**
`domains/simulation/calculator.py`, `domains/applications/state_machine.py`,
`domains/applications/checklist.py`, `domains/applications/affordability.py`,
`domains/documents/file_type.py`, `domains/documents/classification/evaluator.py`.

These are pure functions with a finite number of branches. Full coverage is achievable, meaningful,
and it is where being wrong is unrecoverable.

```bash
pytest --cov=app.domains.simulation.calculator \
       --cov=app.domains.applications.state_machine \
       --cov=app.domains.applications.checklist \
       --cov=app.domains.applications.affordability \
       --cov=app.domains.documents.file_type \
       --cov=app.domains.documents.classification.evaluator \
       --cov-fail-under=100
```

**Module paths, not file paths.** Written as `--cov=app/domains/.../calculator.py`, which is how
this command read until T10, coverage collects nothing: it reports `No data was collected` and a
total of 0%. With `--cov-fail-under=100` that at least fails loudly, but it fails for the wrong
reason and the obvious "fix" is to lower the threshold. Verified both ways at T10.

**T-P6. Tier 2 — everything else: flow-level integration tests, no threshold.**
Services, routers, repositories. Six tests covering the paths a user actually takes. Coverage is
whatever it is; the tests exist to prove the flows work, not to move a number.

This split is worth being able to state out loud. It is a defensible testing position rather than a
compliance ritual.

## Time budget

| Phase | Budget |
|---|---|
| P0 Deploy skeleton | 0:25 |
| P1 Domain core + platform | 1:00 |
| P2 API surface | 1:05 |
| P3 Frontend | 0:50 |
| P4 Integration and review | 0:40 |
| P5 AI classification | 0:30 |
| P6 Ship | 0:25 |
| **Implementation total** | **~4:55** |
| Specs, written earlier | ~1:00 |

**T-P7.** Roughly five hours against a two-hour cap. That is a choice, not an overrun, and the README
states the real number with this split. Track actual time per phase as you go; reconstructing it
afterwards produces a figure nobody believes. The cut table in `0-business-logic.md` §5 is written
against the brief's cap, not against this budget — see the note there.

---

# P0 — Deploy skeleton

Before any feature work. This turns deployment from a risk into a routine (`5-deployment.md`
DEP-040 – DEP-042).

### T01 | Repository skeleton
```
Owner  D
Deps   —
Files  the whole backend tree, once; the Angular scaffold
Output The directory structure from 2-architecture.md ARC-002, every package with
       __init__.py, every module containing only its docstring header;
       `ng new borrower-portal` under frontend/
Tests  —
Done   `find backend/app -name "*.py" | wc -l` → 54; `frontend/angular.json` exists;
       one commit: "chore: repository skeleton [T01]"
```
Empty modules with docstrings only. Every later agent then has a target file that already exists, so
no two invent competing layouts.

**The Angular scaffold belongs here, not in T26.** Two reasons, and the second is blocking. It had no
owner in any ticket — T26 edits `src/app/core/*` but nothing created the project around it. And
T03's Dockerfile stage 1 runs `npm ci` against `frontend/package*.json`: without the scaffold the
container build fails, so a P0 ticket would have depended on a P3 one. The project name is not free
— `5-deployment.md` DEP-008 copies `dist/borrower-portal/browser`.

### T02 | Backend boots
```
Owner  D
Deps   T01
Files  app/main.py, app/core/health.py, app/core/dependencies.py,
       pyproject.toml, poetry.lock, poetry.toml
Output GET /health returning {"status":"ok"}, delegating to a HealthService so
       the controller rule holds from the first endpoint (CQ-017, DEP-015);
       the poetry manifest and committed lock from 5-deployment.md DEP-052;
       pyproject.toml carrying the CQ-076 ruff rule set and the CQ-077 mypy settings
Tests  test_health_returns_ok
Done   `pytest tests/test_health.py -q` → 1 passed
       `ruff check app` reports at least one D/ANN finding against a deliberately
       undocumented throwaway function, proving the rule set is live
```
**The `ruff check` half of the done condition is not ceremony.** With no `[tool.ruff.lint] select`,
ruff runs its defaults and every rule in CQ-076 is silently inactive — `ANN`, `D`, `C901`, `PLR0913`
all off, and T34's gate then passes while checking almost nothing. Prove the configuration is live
here, once, at the point it is written (CQ-096).

### T03 | Container builds
```
Owner  D
Deps   T02
Files  infra/Dockerfile, infra/.dockerignore
Output A three-stage image serving /health on 8080
Tests  —
Done   `docker build -f infra/Dockerfile -t bp .` succeeds and
       `docker run -p 8080:8080 bp` answers /health
```
Verify the Angular output path against `angular.json` now. Angular 17+ emits to
`dist/<project>/browser` (`5-deployment.md` DEP-010).

### T04 | Fly app live
```
Owner  D
Deps   T03
Files  infra/fly.toml
Output A public URL and a 1 GB volume in ams
Tests  —
Done   `curl https://<app>.fly.dev/health` → {"status":"ok"} and `fly volumes list`
       shows the volume
```
**If this is not green, stop and fix it.** Everything after assumes a working pipeline.

### T05 | Agentic setup committed
```
Owner  D
Deps   T01
Files  CLAUDE.md, .claude/, docs/sessions/README.md
Output Project rules for agents; a directory ready to receive session logs
Tests  —
Done   CLAUDE.md exists and docs/sessions/ contains its index file
```
Logs start here. Part C is 20 minutes and they cannot be reconstructed afterwards.

### T43 | Local orchestration
```
Owner  D
Deps   T02
Files  Makefile, .env.example, infra/docker-compose.yml, frontend/proxy.conf.json
Output make dev/test/lint/build/deploy/obs/clean per 5-deployment.md DEP-038;
       every required variable documented with no values (DEP-018, DEP-047);
       the two-service dev stack (DEP-016) and the /api proxy (DEP-017)
Tests  —
Done   `make lint` and `make test` both run; `.env.example` names DATA_DIR,
       JWT_SECRET, ENVIRONMENT, OTEL_EXPORTER_OTLP_ENDPOINT,
       AI_CLASSIFICATION_ENABLED and ANTHROPIC_API_KEY, and no value
```
**Added: these four files were specified and unowned.** `DEP-047` and `DEP-048` are definitions of
done that depended on them, `CQ-079` calls `make lint` the binding gate, and no ticket created any of
it. `ARC-028` assigns them to unit D; this is the ticket that makes that assignment real, because
`T-P2` requires a file to be named by a ticket before an agent may write it.

`make dev` is only half-usable until T26: the `web` service runs `npm ci` against a frontend that
T01 scaffolded but has not yet been themed. The `api` half works from here.

---

# P1 — Domain core and platform

A and D run in parallel. No shared files. C can also start T26 now.

### T06 | Rate conversion
```
Owner  A
Deps   T01
Files  app/domains/simulation/calculator.py
       app/core/enums.py, app/core/errors.py
       tests/domains/simulation/test_calculator.py

Output monthly_rate(annual_rate: Decimal) -> Decimal
       Region and DocumentType, written once here (ARC-044)
       the DomainError hierarchy and the VAL-004 codes (ARC-045): the pure
       modules raise them, so they cannot wait for T14

Tests  test_monthly_rate_uses_actuarial_conversion
       test_monthly_rate_roundtrips_to_annual
       test_monthly_rate_differs_from_naive_division
       test_monthly_rate_zero_returns_zero
       test_monthly_rate_negative_raises

Done   pytest tests/domains/simulation/test_calculator.py -q → 5 passed
```
Test first. `monthly_rate(0.0546)` is `0.00443996` to 8dp; `(1+i)**12 == 1.0546` within 1e-12; it is
**not** `0.0546/12`. → `SIM-001` – `SIM-003`, `AC-002`.

`test_monthly_rate_differs_from_naive_division` is a regression guard, not a formula check. It exists
so nobody "simplifies" this in six months.

### T07 | Annuity and schedule
```
Owner  A
Deps   T06
Files  app/domains/simulation/calculator.py
       app/domains/simulation/entities.py
       tests/domains/simulation/test_calculator.py

Output annuity(principal, periodic_rate, term_months) -> Decimal
       (named periodic_rate, not monthly_rate: the latter is the function
       above it in the same module, and shadowing it reads as a bug)
       build_amortisation_schedule(principal, annual_rate, term_months) -> AmortisationSchedule
       AmortisationSchedule(monthly_payment, entries, total_interest, total_paid)

Tests  test_annuity_matches_kbc_published_example
       test_annuity_zero_rate_returns_principal_over_term
       test_annuity_naive_division_overstates_payment
       test_schedule_closes_at_exactly_zero
       test_schedule_principal_sums_to_loan_amount
       test_schedule_final_instalment_absorbs_rounding

Done   pytest -q → 11 passed
```
KBC: 170 000 / 240 / 5.46% → `1152.95` ± 0.02 against the published 1152.96. Naive division gives
`1165.57`, off by €12.62 a month. → `SIM-004` – `SIM-009`, `AC-001`, `AC-006`.

### T08 | Upfront costs
```
Owner  A
Deps   T06
Files  app/domains/simulation/calculator.py
       app/domains/simulation/entities.py
       tests/domains/simulation/test_upfront_costs.py

Output registration_duty(property_value, region, is_first_home) -> Decimal
       compute_upfront_costs(request, loan_amount) -> UpfrontCosts
       SimulationInput and UpfrontCosts entities. `request` here is the entity,
       not the pydantic schema (ARC-043); taking the five fields as separate
       parameters would breach CQ-038's four-parameter limit anyway.

Tests  test_registration_duty_regional_matrix          [parameterised, 6 cases]
       test_brussels_abattement_never_returns_negative
       test_brussels_below_abattement_returns_zero
       test_upfront_total_is_sum_of_components
       test_total_cash_needed_includes_own_contribution

Done   pytest tests/domains/simulation/test_upfront_costs.py -q → 10 passed
       (5 functions; the AC-004 matrix parameterises into 6 cases)
```
The six-case matrix is `AC-004`. Brussels at 150 000 first-home must return exactly `0.00`, never a
negative number. → `SIM-010` – `SIM-013`.

### T09 | JKP
```
Owner  A
Deps   T07, T08
Files  app/domains/simulation/calculator.py
       tests/domains/simulation/test_jkp.py

Output compute_jkp(loan_amount, monthly_payment, term_months, fees) -> Decimal

Tests  test_jkp_exceeds_nominal_rate
       test_jkp_primary_case_matches_expected
       test_jkp_excludes_registration_duty_and_purchase_notary
       test_jkp_with_zero_fees_equals_nominal_rate
       test_jkp_computation_failure_raises_domain_error

Done   pytest tests/domains/simulation/test_jkp.py -q → 6 passed
```
Bisection. Fee base includes `mortgage_costs`, `dossier_fee`, `valuation_fee`. Excludes
`registration_duty` and the purchase-deed notary fee. Primary case ≈ `0.0414`.
→ `SIM-015` – `SIM-019`, `AC-008`.

### T10 | Full simulation
```
Owner  A
Deps   T07, T08, T09
Files  app/domains/simulation/calculator.py
       tests/domains/simulation/test_simulate.py

Output simulate(request: SimulationInput) -> SimulationResult
       (an orchestrator, per the function rules in 1-code-quality.md CQ-036 – CQ-037)

       SimulationInput, SimulationResult, AmortisationSchedule and UpfrontCosts are domain
       entities in entities.py, not the pydantic wire schemas — 2-architecture.md ARC-043.
       calculator.py may not import a schema (ARC-013); the service converts.

Tests  test_simulate_primary_case_full_output
       test_simulate_first_home_flip_changes_cash_by_thirty_thousand
       test_simulate_zero_own_contribution_flags_above_norm
       test_simulate_quotiteit_exactly_ninety_is_not_flagged
       test_simulate_own_contribution_equals_price_raises
       test_simulate_all_money_values_are_decimal

Done   pytest tests/domains/simulation/ -q → 33 passed
       pytest --cov=app.domains.simulation.calculator --cov-fail-under=100

       33, not the 27 this ticket first recorded. T08's tax matrix is
       parameterised over six rows (AC-004) and pytest counts cases, not
       functions; the earlier arithmetic counted it once. One test was also
       added to T09 to reach 100% on the CQ-054 translation branch.
```
Primary case: `1414.52` / `424356.04` / `154356.04` / `43175.00`. Flipping `is_first_home` changes
cash needed by exactly `30000.00`. → `AC-003`, `AC-005`, `DOM-016`, `VAL-009`.

### T11 | State machine
```
Owner  A
Deps   T01
Files  app/domains/applications/state_machine.py
       tests/domains/applications/test_state_machine.py

Output ALLOWED_TRANSITIONS mapping
       assert_transition(current, target) -> None

Tests  test_every_allowed_transition_passes           [parameterised]
       test_every_disallowed_transition_raises        [parameterised]
       test_documents_complete_can_return_to_pending
       test_submitted_cannot_return_to_draft
       test_withdrawn_is_terminal

Done   pytest tests/domains/applications/test_state_machine.py -q → all passed
       coverage on state_machine.py is 100%
```
`DOCUMENTS_COMPLETE → DOCUMENTS_PENDING` is allowed. It is the first-time-right loop, not an error
path. → `APP-001` – `APP-009`.

### T12 | Checklist
```
Owner  A
Deps   T01
Files  app/domains/applications/checklist.py
       tests/domains/applications/test_checklist.py

Output required_documents(application) -> list[DocumentRequirement]
       DocumentRequirement(doc_type, label_en, label_nl, required, reason)

Tests  test_base_requirements_always_present
       test_employee_adds_payslips_and_employer_statement
       test_self_employed_adds_tax_assessment_and_accountant_statement
       test_existing_property_adds_epc
       test_new_build_adds_permit_and_quote
       test_existing_credit_adds_loan_statements
       test_requirement_satisfied_by_any_document_of_type
       test_conditional_requirements_carry_a_reason
       test_changing_employment_type_changes_required_set

Done   pytest tests/domains/applications/test_checklist.py -q → 9 passed
       coverage on checklist.py is 100%
```
→ `DOC-005` – `DOC-009`, `API-046`.

### T13 | Database core
```
Owner  D
Deps   T02
Files  app/core/database.py, app/core/config.py
Output engine, async_sessionmaker, Base, get_session dependency, pragma setup
Tests  test_foreign_keys_pragma_is_on
       test_journal_mode_is_wal
       test_session_dependency_yields_and_closes
Done   pytest tests/core/test_database.py -q → 3 passed; app.db appears under DATA_DIR
```
→ `ARC-039`, `CQ-080` – `CQ-084`.

### T14 | Errors, handlers and request guards
```
Owner  D
Deps   T02
Files  app/core/exception_handlers.py, app/main.py,
       app/core/rate_limit.py, app/core/limits.py
Output handlers rendering {"code","message","field"} for every code in the
       registry, 7-validation.md §2 (VAL-004) — the hierarchy itself lands in
       T06, which is the first code that raises one;
       the two request-level guards that raise registry codes —
       TOO_MANY_ATTEMPTS (AUTH-040) and DOCUMENT_TOO_LARGE (VAL-024)
Tests  test_domain_error_renders_expected_shape
       test_pydantic_error_normalised_to_same_shape
       test_every_declared_code_maps_to_a_status
       test_error_response_contains_no_stack_trace
Done   pytest tests/core/test_errors.py tests/core/test_limits.py
       tests/core/test_rate_limit.py -q → all passed
       (main.py is in the file list because a handler that is never registered
       maps nothing; ARC-014 makes this the only module that may do it)
```
→ `VAL-004` – `VAL-007`, `API-013` – `API-015`, `CQ-053`.

### T15 | Logging and telemetry
```
Owner  D
Deps   T02
Files  app/core/logging.py, app/core/telemetry.py,
       observability/otel-collector.yaml,
       observability/docker-compose.observability.yml,
       observability/grafana/datasources.yml
Output structlog JSON config, request_id middleware, X-Request-ID header,
       redaction denylist, OTel setup; the collector and Grafana configuration
       that DEP-007 and DEP-033 require and no ticket previously owned
Tests  test_log_line_is_json_with_request_id
       test_response_carries_request_id_header
       test_email_is_redacted_from_log_output
       test_amount_is_redacted_from_log_output
Done   pytest tests/core/test_logging.py -q → 4 passed
```
→ `DEP-029` – `DEP-032`, `DEP-035`.

### T16 | Blob storage, and readiness
```
Owner  D
Deps   T02, T13
Files  app/core/storage.py, app/core/health.py, app/main.py
Output StorageBackend protocol; LocalStorage implementation;
       HealthService.readiness() and the GET /ready route
Tests  test_save_returns_generated_key
       test_load_roundtrips_content
       test_path_traversal_filename_cannot_escape_blob_root
       test_missing_key_raises_domain_error
       test_ready_returns_ready_when_both_stores_are_usable
       test_ready_returns_503_when_the_blob_directory_is_unwritable
Done   pytest tests/core/test_storage.py tests/core/test_ready.py -q → 6 passed
```
→ `CQ-033`, `CQ-034`, `DOC-003`, `VAL-023`, `DEP-037`, `DEP-050`.

**`/ready` is added here because it had no owning ticket at all.** `DEP-037` and `DEP-050` require
it and `DEP-040` step 5 asks for it as soon as `core/database.py` exists, but no ticket named it.
T16 is the earliest point where it can be *complete*: `ARC-010` keeps `core.database` and
`core.storage` deliberately separate, and `DEP-037` probes one of each. It is `async def`, unlike
`/health`, because this one genuinely awaits (`DEP-054`).

### T44 | Test fixtures
```
Owner  D
Deps   T13
Files  tests/conftest.py
Output An in-memory async engine and session fixture, a FastAPI app fixture with
       get_session overridden, an httpx.AsyncClient fixture, a tmp blob root
Tests  —
Done   `pytest -q` collects with no fixture errors; T17 and T25 import nothing local
```
**Added: `tests/conftest.py` is in the ARC-002 tree and was owned by no ticket.** It is the one file
units A, B and D all need — T13 for the session, T17 for the repositories, T25 for the flow tests —
so leaving it unowned guarantees the collision `T-P2` exists to prevent: three agents writing the
same file. It lands before Sync point 1 so P2 opens with fixtures already there.

**Sync point 1.** A's signatures and D's session dependency exist. P2 can start.

---

# P2 — API surface

### T17 | Tables and repositories
```
Owner  B
Deps   T13
Files  each domain's tables.py and repository.py
Output Five tables; repositories returning domain entities
Tests  test_create_all_builds_every_table
       test_users_email_unique_index_exists
       test_repository_returns_domain_model_not_orm_row
       test_money_columns_load_as_decimal
Done   pytest tests/domains/*/test_repository.py -q → 4 passed
```
→ `CQ-085` – `CQ-088`, `ARC-038`, `ARC-040`.

### T18 | Simulation endpoints
```
Owner  B
Deps   T10, T17, T14
Files  app/domains/simulation/{router,service,schemas}.py
Output POST /api/simulations, GET /api/simulations/{id}
Tests  test_create_simulation_returns_primary_case_body
       test_create_simulation_persists_and_is_retrievable
       test_money_fields_serialise_as_strings
       test_own_contribution_equal_to_price_returns_422
       test_term_out_of_range_returns_422
       test_extra_field_is_rejected
       test_unknown_simulation_returns_404
Done   pytest tests/domains/simulation/test_api.py -q → 7 passed
```
→ `API-018` – `API-022`, `CQ-017`.

### T19 | Auth
```
Owner  B
Deps   T17, T14
Files  app/domains/auth/*
Output signup, login, logout, me; current_user dependency
Tests  test_signup_sets_httponly_samesite_cookie
       test_signup_duplicate_email_returns_409
       test_signup_duplicate_email_race_caught_by_integrity_error
       test_login_wrong_password_and_unknown_email_are_identical
       test_login_hashes_even_when_user_missing
       test_me_without_cookie_returns_401
       test_tampered_token_returns_401
       test_startup_fails_without_jwt_secret
Done   pytest tests/domains/auth/ -q → 8 passed
```
`current_user` lives in `app/domains/auth/dependencies.py`, **not** `app/core/dependencies.py`:
`core` may not import a domain (`ARC-012`), which is exactly why `ARC-042` made the auth dependency
module a second public surface of the domain. → `AUTH-021` – `AUTH-038`.

### T20 | Simulation claim
```
Owner  B
Deps   T18, T19
Files  app/domains/auth/service.py, app/domains/simulation/service.py
Output claim_for_user; signup claiming inside one transaction
Tests  test_signup_with_simulation_claims_it
       test_signup_with_unknown_simulation_still_succeeds
       test_signup_with_claimed_simulation_does_not_reassign
       test_claim_and_user_insert_share_one_transaction
       test_post_applications_seeds_the_draft_from_the_claimed_simulation
Done   pytest tests/domains/auth/test_claim.py -q → 4 passed
```
→ `DOM-025` – `DOM-027`, `ARC-017`, `AUTH-030` – `AUTH-032`, `CQ-091`.

### T21 | Application endpoints
```
Owner  B
Deps   T11, T17, T19
Files  app/domains/applications/{router,service,schemas}.py
Output list, get, patch, submit
Tests  test_list_returns_only_own_applications
       test_other_users_application_returns_404_not_403
       test_patch_updates_only_present_fields
       test_patch_rejects_status_field
       test_submit_transitions_to_submitted
       test_double_submit_returns_409
       test_submit_with_missing_field_returns_422_with_field_name
Done   pytest tests/domains/applications/test_api.py -q → 7 passed
```
→ `API-029` – `API-044`, `AUTH-035`, `API-011`.

### T22 | Checklist endpoint — in the documents domain
```
Owner  B
Deps   T12, T21
Files  app/domains/documents/{router,service}.py
       app/domains/applications/service.py  (checklist(), taking uploaded types)
Output GET /api/applications/{id}/checklist
Tests  test_checklist_returns_counts_and_items
       test_conditional_item_carries_reason
       test_changing_employment_type_changes_checklist_response
       test_checklist_of_other_users_application_returns_404
Done   pytest tests/domains/applications/test_checklist_api.py -q → 4 passed
```
→ `API-045` – `API-047`, `UX-038`.

### T23 | Document endpoints
```
Owner  B
Deps   T16, T22
Files  app/domains/documents/*
Output file_type.detect_content_type (pure, Tier 1 — owned by no ticket
       before T23 despite being in the T-P5 coverage command);
       upload, download, delete
Tests  test_detect_content_type_recognises_pdf_jpeg_png
       test_detect_content_type_rejects_an_unknown_signature
       test_detect_content_type_ignores_the_extension
       test_upload_pdf_succeeds_and_returns_application_status
       test_upload_txt_renamed_as_pdf_is_rejected_415
       test_upload_oversize_rejected_413_before_buffering
       test_upload_empty_file_rejected_422
       test_upload_type_not_in_checklist_rejected_422
       test_upload_and_status_change_share_one_transaction
       test_delete_last_satisfying_document_returns_pending
       test_download_of_other_users_document_returns_404
Done   pytest tests/domains/documents/ -q → 8 passed
```
→ `API-048` – `API-056`, `VAL-022` – `VAL-025`, `ARC-018`, `CQ-091`.

### T24 | SPA serving
```
Owner  D
Deps   T02
Files  app/main.py
Output Catch-all returning index.html for non-API routes
Tests  test_deep_route_returns_index_html
       test_api_route_still_resolves
       test_unknown_api_route_returns_404_not_index
Done   pytest tests/test_spa.py -q → 3 passed
```
Route order: API routers first, catch-all last. → `DEP-013` – `DEP-015`.

### T25 | API integration tests
```
Owner  B
Deps   T23, T24
Files  tests/integration/test_flows.py
Output Six flow tests over httpx.AsyncClient against an in-memory database

Tests  test_flow_simulate_signup_apply_upload_end_to_end
       test_flow_anonymous_simulation_survives_into_application
       test_flow_document_removal_moves_application_backwards
       test_flow_unauthenticated_access_is_rejected_everywhere
       test_flow_user_cannot_reach_another_users_resources
       test_flow_validation_errors_use_the_shared_error_shape

Done   pytest tests/integration/ -q → 6 passed
```
This is Tier 2 in full (T-P6). Six tests over the paths a user actually takes, no coverage threshold.

**Sync point 2.** The wire contract is real. C is unblocked (`ARC-029`).

---

# P3 — Frontend

### T26 | Shell, theme, HTTP core
```
Owner  C
Deps   T01
Files  src/styles.css, src/app/core/*, app.config.ts, app.routes.ts,
       eslint.config.js, playwright.config.ts, e2e/
Output Tailwind v4 @theme matching 3-ui.md; PrimeNG preset with cssLayer order;
       api client, error interceptor, auth interceptor;
       eslint.config.js carrying the CQ-078 rule set (CQ-096);
       Playwright installed and wired into `make test` (UI-068, UX-062)
Tests  —
Done   `npm run build` succeeds; `make lint` passes, which is where the UI-027
       and UI-030/UI-064 shell checks now live (5-deployment.md DEP-038)
```
Can start before the backend exists. Those two checks are the machine enforcement for `UI-027`,
`UI-030` and `UI-064` that `3-ui.md` Appendix B recorded as not yet existing. They sit in `make lint`
rather than in this done condition so they keep firing after the ticket closes. **The hex grep
excludes `src/app/core/theme/`**: `UI-039` mandates a PrimeNG preset written as hex literals, so a
blanket ban on hex in `.ts` would have failed against the file the same spec requires — `UI-030` now
names both token surfaces.
→ `UI-024` – `UI-039`, `ARC-037`.

### T27 | Simulator
```
Owner  C
Deps   T26, T18
Files  src/app/domains/simulation/*
Output Simulator page, form, result panel, cost breakdown
Tests  test_simulator_renders_result_on_first_paint
       test_previous_result_stays_visible_during_recalculation
       test_above_norm_chip_appears_over_ninety_percent
Done   `npm test -- --include=**/simulation/**` passes;
       e2e: result on first paint (UX-055), previous result survives a change
       (UX-056), chip appears above 90% and is not an error (UX-057)
```
→ `UX-009` – `UX-017`, `UI-047` – `UI-051`.

### T28 | Auth screens and guard
```
Owner  C
Deps   T26, T19
Files  src/app/domains/auth/*
Output Signup, login, route guard
Tests  test_signup_sends_simulation_id
       test_401_redirects_preserving_target_url
Done   `npm test -- --include=**/auth/**` passes;
       `grep -r "localStorage" src` returns nothing
```
→ `AUTH-044` – `AUTH-049`, `AUTH-053`.

### T29 | Application wizard
```
Owner  C
Deps   T26, T21
Files  src/app/domains/application/*
Output Four-step stepper with server-side draft saving
Tests  test_only_current_step_validates
       test_back_preserves_entered_data
Done   `npm test -- --include=**/application/**` passes;
       e2e: a mid-wizard reload keeps step 1 (UX-059)
```
→ `UX-029` – `UX-035`, `UI-054`.

### T30 | Documents and checklist
```
Owner  C
Deps   T26, T23
Files  src/app/domains/documents/*
Output Checklist with per-requirement upload
Tests  test_reason_is_displayed_for_conditional_items
       test_failed_upload_reverts_the_row
Done   `npm test -- --include=**/documents/**` passes; each row has its own upload
       control; e2e: the whole flow completes at 375px (UX-061, UI-067)
```
→ `UX-036` – `UX-043`, `UI-052`.

---

# P3.5 — UI polish (user-directed)

Not part of the original 44-ticket plan. The user ran the deployed batch-4 frontend by hand — the
first real look this build had gotten in a browser rather than through DOM-text assertions — and
found a genuine correctness bug plus a list of visual/UX gaps. Same discipline as every other batch:
one ticket, one commit, spec first.

### T45 | Fix: an invalid intermediate value permanently kills live recompute
```
Owner  C
Deps   T27
Files  src/app/domains/simulation/pages/simulator-page.component.ts,
       simulator-page.component.spec.ts, e2e/simulator.spec.ts
Output filter(form.valid) before switchMap; catchError inside switchMap's
       inner observable instead of at the outer subscribe
Tests  test_invalid_intermediate_value_never_reaches_the_network
       test_a_failed_request_does_not_stop_future_recomputation
Done   `npm test -- --include=**/simulation/**` passes; e2e: clearing a field
       mid-edit and retyping does not freeze the panel
```
Found by the user by hand, not by any automated check: an uncaught HTTP error propagating through
`switchMap` terminates an RxJS subscription permanently, not just for the request that failed —
`takeUntilDestroyed()` only guards against component destruction, not this.
→ `UX-063`.

### T46 | Home screen and routing split
```
Owner  C
Deps   T26
Files  src/app/domains/home/*, app.routes.ts, core/shell/app-header.component.ts
Output Marketing home page at `/`; simulator moves to `/calculator`
Tests  —
Done   `make e2e` green with the updated routes; home renders its hero and
       both CTAs navigate correctly
```
→ `UI-069`, corrected `UI-054`.

### T47 | Auth screens — Google-style split layout
```
Owner  C
Deps   T28
Files  src/app/domains/auth/components/auth-branding-panel.component.*,
       signup-page.component.html, login-page.component.html
Output Two-column form + branding layout, single column on mobile
Tests  —
Done   `make lint` clean (UI-027/UI-030 shell checks); visual check at
       `md:` and mobile widths
```
→ corrected `UI-054`.

### T48 | Dark mode
```
Owner  C
Deps   T26
Files  styles.css, app.config.ts, index.html, core/theme/theme.service.ts,
       core/theme/theme-toggle.component.ts, core/shell/app-header.component.ts
Output Toggle in the header; persisted preference; PrimeNG darkModeSelector
Tests  test_theme_toggle_persists_and_flips_the_class
Done   `ng test` passes; contrast re-checked against UI-060 for the dark
       palette, not assumed from the light one
```
Supersedes `UX-053`'s "not doing" and reasons against `UI-001`'s conclusion without discarding its
legibility concern — the dark palette is contrast-checked, not a naive invert, and light stays the
default.
→ `UX-064`, `UI-071`, `UI-072`.

### T49 | Quotiteit above the norm — clearer, still not an error
```
Owner  C
Deps   T27
Files  simulation-result.component.html, simulation-form.component.html
Output Chip states the actual quotiteit figure; a live micro-hint under Own
       contribution echoes the same figure at the input
Tests  —
Done   Visual check; still `bg-signal-soft text-ink`, never `danger`
```
`DOM-016`/`ERR-006` do not change: above 90% stays informational, never an error. The fix is a
clearer number, not an alarm.
→ corrected `UX-017`.

### T50 | PrimeNG Community License
```
Owner  C
Deps   T26
Files  frontend/.env (gitignored), .env.example, scripts/generate-env.mjs,
       package.json, app.config.ts, .gitignore
Output License key read from a gitignored .env via a prestart/prebuild
       codegen step, never committed
Tests  —
Done   Console no longer warns `[PrimeUI] ... unconfigured`; no license
       banner
```

### T51 | Test ripple and new coverage
```
Owner  C
Deps   T46, T48
Files  e2e/*.spec.ts (route fix), e2e/home.spec.ts, e2e/theme.spec.ts,
       theme.service.spec.ts
Output Existing specs updated for the `/` → `/calculator` move; new coverage
       for the home page and the theme toggle
Tests  test_theme_persists_across_reload
Done   `make e2e` green
```

### T52 | Batch verification
```
Owner  C
Deps   T45 – T51
Files  —
Output —
Done   `npm run build`, `ng test`, `make e2e`, `make lint` all green; a real
       visual pass in a browser at `/`, `/calculator`, `/signup`, `/login`,
       both themes — not just DOM-text assertions, the gap that let T45's
       bug and the missing Tailwind compilation through in the first place
```

---

# P7 — Documents produce data

Added after batch 4.5, when the question "what does this project actually *do* with an uploaded
document?" turned out to have the honest answer: nothing. A document satisfies a checklist row by the
type the borrower declared and is never opened again.

**The rule that makes this one feature rather than three: a document produces a *proposal*, the
borrower confirms it, and only confirmed data is ever calculated on.** That extends `AI-003` ("the
model advises, deterministic code owns the outcome") from a document's *type* to its *values* instead
of contradicting it, and it makes manual entry the base case rather than a bolt-on — the same form,
with nothing pre-filled. With `AI_CLASSIFICATION_ENABLED=false` the borrower types everything and the
product still works end to end, so `AI-039` holds by construction.

**Ordering note.** `AI-001` puts classification last, after every flow works on the deployed URL. T31
is run first to satisfy exactly that; the rest of P4 (T32 – T34) is deliberately deferred. That is a
conscious reordering, recorded here rather than left to be noticed.

### T53 | Affordability calculator
```
Owner  A
Deps   —
Files  app/domains/applications/affordability.py
       app/domains/applications/entities.py
       tests/domains/applications/test_affordability.py

Output assess(profile, monthly_payment) -> AffordabilityAssessment
       DSTI and restleefgeld bands; every threshold a named constant

Tests  test_residual_floor_single_adult_no_dependants_is_the_base
       test_residual_floor_second_adult_raises_it
       test_residual_floor_each_dependant_raises_it
       test_residual_floor_clamps_nonsensical_household_sizes
       test_assess_bands_the_income_share
       test_assess_residual_exactly_on_the_floor_is_tight_not_outside
       test_assess_residual_below_the_floor_is_outside_typical_norms
       test_assess_takes_the_worse_of_the_two_measures
       test_assess_missing_income_returns_insufficient_data
       test_assess_non_positive_income_returns_insufficient_data
       test_assess_existing_credit_counts_towards_the_obligations
       test_assess_absent_existing_credit_is_treated_as_zero
       test_assess_never_reports_a_decision
       test_ac009_primary_case_on_a_modest_income_is_outside_norms
       test_ac009_the_same_household_on_a_higher_income_is_comfortable

Done   pytest tests/domains/applications/test_affordability.py -q → 17 passed
       coverage on affordability.py is 100%
```
Supersedes the `SCP-011` cut. Pure, fourth module beside `checklist.py` and `state_machine.py`; takes
the monthly payment as a `Decimal` argument so it never imports the simulation domain. The output is
a **band, never a decision** — nothing in the state machine reads it.
→ `SIM-022` – `SIM-029`, `DOM-029`, `DOM-030`, `AC-009`.

### T54 | The confirmed financial profile
```
Owner  A
Deps   T53
Files  app/domains/applications/{entities,tables,repository,schemas,service,router}.py
       app/domains/simulation/service.py        (monthly_payment_for, ARC-047)
       tests/domains/applications/test_financials_api.py
       tests/domains/test_repositories.py       (the table-set assertion)

Output application_financials table, one row per application, with provenance;
       GET/PUT /api/applications/{id}/financials returning profile + assessment

Tests  test_get_financials_is_empty_before_anything_is_saved
       test_put_records_manual_provenance
       test_put_rejects_a_client_supplied_provenance
       test_put_returns_the_assessment_for_the_saved_figures
       test_put_counts_existing_credit_towards_the_obligations
       test_put_replaces_the_profile_wholesale
       test_financials_survive_a_borrower_patch
       test_assessment_is_absent_without_a_linked_simulation
       test_another_users_financials_return_404_not_403
       test_put_rejects_a_negative_income

Done   pytest tests/domains/applications/test_financials_api.py -q → 10 passed
```
**A table of its own, not columns on `borrowers`** — `API-037` replaces that collection wholesale on
every PATCH, so a confirmed figure stored there would be destroyed by the borrower editing their own
name. `test_financials_survive_a_borrower_patch` is the test that pins it.

Provenance is recorded by the server, never accepted from the client: a self-reported audit trail is
not an audit trail. Every figure written here is `MANUAL`, because extraction does not exist yet.

`monthly_payment_for()` is the second method on the `ARC-047` edge, for the same reason `get_owned`
became the second on `ARC-018` — only the simulation domain may run its calculator, and DOM-001 says
the payment is recomputed rather than stored.
→ `API-073` – `API-077`, `DOM-029`, `DOM-030`.

### T55 | Finances capture and the affordability panel
```
Owner  C
Deps   T54
Files  src/app/domains/application/components/finances-section.component.{ts,html}
       src/app/domains/application/{application.models.ts,application.service.ts}
       src/app/domains/application/pages/application-wizard.component.{ts,html}
       src/app/core/api-client.service.ts        (put(), which had no caller before)

Output The finances form and the affordability result on the application page
Tests  the existing wizard spec, extended for the financials request

Done   `npm run build` succeeds; a borrower who uploads nothing can type an
       income and get a band back — the end-to-end proof that the AI layer is
       optional (AI-039, proven before the AI layer exists)
```
The whole of Group A closes here. With `AI_CLASSIFICATION_ENABLED` never having been switched on —
and, at this point, nothing behind it even built — the product answers *can I afford this* end to
end. That is the property the plan is arranged around: extraction pre-fills these fields later and
changes nothing else.
→ `UX-065`, `UX-066`, `SIM-028`.

### T62 | Fix: a reload dropped the anonymous simulation
```
Owner  C
Deps   T55
Files  src/app/domains/simulation/simulation.service.ts
       src/app/domains/simulation/simulation.service.spec.ts
       src/app/domains/auth/pages/signup-page.component.ts
       e2e/simulation-claim.spec.ts

Output The held simulation id survives a reload (sessionStorage, one tab) and
       is dropped once claimed

Tests  remembers the simulation id across a reload (DOM-026)
       forgets the id once it has been claimed (DOM-027)
       starts empty in a fresh tab
       e2e: a reload between simulating and signing up still claims it

Done   `make e2e` green; the new scenario fails with the fix reverted
```
Found by hand while verifying T55, not by any check. The id lived only in a signal, so refreshing or
typing `/signup` into the address bar dropped it. Signup still succeeded — `UX-028` requires that —
so the failure was silent, and the draft was simply created unseeded. Once T53/T54 existed the cost
grew: no seeded simulation means no instalment, and `API-075` then returns a null assessment.

The regression test was confirmed to have teeth by reverting the fix and watching it fail.
→ `DOM-026` (corrected), `DOM-027`.

---

# P4 — Integration

### T31 | Deployed end to end
```
Owner  you
Deps   T24, T25, T27–T30
Output A working public URL
Tests  —
Done   `fly deploy` succeeds; the full flow runs on the public URL
```
→ `SCP-019`, `DEP-043`.

### T32 | Manual edge-case run
```
Owner  you
Deps   T31
Output —
Tests  —
Done   All 18 steps of 7-validation.md §8 (VAL-027) pass in a 375px-wide window
```
→ `UX-061`, `VAL-033`.

### T33 | Read every diff
```
Owner  you
Deps   T31
Output —
Tests  —
Done   `git log -p` reviewed end to end; nothing in the repository is unexplained
```
**Not optional.** Part B is 15 minutes walking through this code on a shared screen. A file you
cannot explain is worse than a file that does not exist. Anything unclear is rewritten or deleted
now.

### T34 | Full suite and coverage gate
```
Owner  you
Deps   T33
Output —
Tests  —
Done   `make test` passes; the Tier 1 coverage command reports 100%;
       `ruff check` and `mypy --strict app` are clean **against the configuration
       committed in T02** — a green run with no pyproject.toml proves nothing
```
This is `CQ-079` — the gate that stands in for CI, which is a deliberate non-goal
(`1-code-quality.md` §13). → `DEP-038`.

**Gate: P5 does not start until T31–T34 are all green.** This is `AI-001`.

---

# P5 — AI classification

Only past the gate. Spec in [`9-ai-classification.md`](9-ai-classification.md).

### T35 | Decision layer
```
Owner  A
Deps   gate
Files  app/domains/documents/classification/{entities,evaluator}.py
       tests/domains/documents/test_evaluator.py

Output evaluate(verdict, claimed) -> ClassificationOutcome
       CONFIDENCE_FLOOR and HIGH_CONFIDENCE as named constants
       ClassifiedType / ClassificationVerdict / ClassificationOutcome as domain
       types, so evaluator.py imports no framework and stays pure (ARC-013)

Tests  test_below_confidence_floor_returns_inconclusive_despite_sharp_mismatch
       test_matching_type_above_floor_returns_confirmed
       test_unknown_above_floor_returns_unrecognised
       test_mismatch_medium_confidence_returns_possible_mismatch
       test_mismatch_high_confidence_returns_likely_mismatch
       test_decision_table_is_covered_end_to_end        (parameterised, AI-034)
       test_thresholds_are_module_constants_not_literals
       test_every_document_type_has_a_classified_counterpart
       test_unknown_is_not_a_document_type

Done   pytest tests/domains/documents/test_evaluator.py -q → 16 passed
       coverage on evaluator.py and entities.py is 100%
```
Pure function, no network, written first. The first test is the one that proves code owns the
outcome, not the model: the model is maximally wrong — a passport called a construction quote — and
the answer is still silence, because the confidence was below the floor.

`ClassificationVerdict` is a frozen dataclass here rather than the pydantic model `AI-011` sketches.
The pydantic model parses the API response and belongs to `client.py` (T36); splitting them is what
keeps `evaluator.py` importable without a framework, the same discipline `ARC-013` already applies to
`calculator.py` and `checklist.py`. `entities.py` is a new file in the classification package,
recorded in `ARC-002`.
→ `AI-011` – `AI-017`, `AI-033` – `AI-034`.

### T36 | Model client
```
Owner  B          (ARC-028 names classification/{client,prompts}.py in unit B)
Deps   T35
Files  app/domains/documents/classification/{client,prompts}.py
       tests/domains/documents/test_client.py
Output render_first_page(content, content_type) -> PNG bytes
       ClassificationClient.classify(page_png) -> ClassificationVerdict
       ClassificationError for transport failures only
Tests  test_a_well_formed_answer_becomes_a_verdict
       test_malformed_json_degrades_to_unknown_zero_confidence  (8 cases)
       test_filename_is_never_included_in_the_request
       test_a_transport_failure_raises_rather_than_degrading
       test_the_model_and_cap_are_sent_as_configured
       test_only_first_page_is_rendered_and_downscaled
       test_a_small_image_is_not_upscaled
       test_unrenderable_bytes_raise_rather_than_returning_a_verdict
Done   pytest tests/domains/documents/test_client.py -q → 15 passed,
       entirely mocked: no key, no network, no cost
```
**Two failure modes, deliberately kept apart.** A *malformed answer* is not a failure — invalid JSON,
an unknown category, a confidence of 2.0, an empty body all degrade to `UNKNOWN` at 0 (`AI-011`),
which the evaluator then bands `INCONCLUSIVE` and the borrower is told nothing. A *transport failure*
is: it raises `ClassificationError`, and T37 turns that into `FAILED`, which renders as nothing
(`AI-021`).

`ClassificationError` is a plain exception, not a `DomainError`: domain errors carry a registry code
and map to an HTTP status (`CQ-053`), and this one must never reach the borrower at all.

The model constant is `claude-sonnet-5` at 300 tokens while the answer is four fields, exactly as
`AI-013` reasons. It changes at T57, where the same call also has to read numbers off the page.
→ `AI-007` – `AI-013`, `AI-022`, `AI-035`.

### T37 | Pipeline and flag
```
Owner  B
Deps   T36, T23
Files  app/domains/documents/classification/pipeline.py
       app/domains/documents/{service,router,repository,tables,dependencies}.py
       app/core/database.py            (background_session)
       tests/domains/documents/test_pipeline.py
Output ClassificationPipeline.run(); two advisory columns; the flag wiring
Tests  test_flag_off_skips_classification_entirely
       test_upload_succeeds_when_classifier_raises
       test_failed_classification_is_recorded_without_an_outcome
       test_outcome_never_changes_doc_type_or_satisfaction
       test_a_deleted_document_is_not_an_error_to_annotate
       test_every_status_is_a_plain_string
Done   pytest tests/domains/documents/test_pipeline.py -q → 9 passed
```
`test_upload_succeeds_when_classifier_raises` is the one to point at on the walkthrough — it proves
`AI-005`: the classifier throws, and the 201, the row, the checklist count and the application status
are all still exactly what the upload made them.

**Two columns, not one** (clarifying `AI-020`, whose list mixed both). `classification_status` is the
lifecycle — `PENDING` / `DONE` / `FAILED` / `SKIPPED`, "did this run at all". `classification_outcome`
is the evaluator's verdict and is null unless the status is `DONE`. One column carrying both would
make "failed" and "inconclusive" the same value, and they have different causes.

**The flag is structural, not conditional** (`AI-024`): with it off, `_get_classifier()` returns None,
so no client is constructed and `ANTHROPIC_API_KEY` is never read. The service's `classifier` is
`None` and scheduling is a no-op, leaving both columns null.

`background_session()` is new in `core/database.py`: the request session closes when the response is
sent, so a task that runs *after* the commit must own one. `BackgroundTasks` reaches the service
through `DocumentContext`, the bundle that already exists to keep handlers inside `CQ-038`'s four
slots.
→ `AI-004` – `AI-006`, `AI-018` – `AI-024`, `AI-036` – `AI-037`.

### T38 | Classification in the UI
```
Owner  C
Deps   T37
Files  src/app/domains/documents/*
Output Row states for pending, confirmed, mismatch
Tests  test_failed_and_skipped_render_as_nothing
       test_likely_mismatch_offers_keep_anyway
Done   `npm test -- --include=**/documents/**` passes
```
→ `AI-021`, `AI-025` – `AI-027`, `AI-041`.

---

# P6 — Ship

### T39 | Final deploy
```
Owner  you
Deps   P5 or the gate, whichever is last
Done   fly deploy; the 18-step run passes again on the deployed URL;
       after `fly apps restart`, a pre-restart user can still log in and see their documents
```
→ `DEP-045`, `AUTH-058`.

### T40 | README
```
Owner  you
Deps   T39
Output README.md
Done   Covers what was built, what was deliberately not built and why, architecture in a
       few lines, one command to run locally, trade-offs forced by the cap, honest AI usage
       with the real time spent
```
Most of it exists already: the cut table in `0-business-logic.md` §5, the trade-offs in
`5-deployment.md`, the known gaps in `6-auth.md` (AUTH-020, AUTH-033, AUTH-041),
`7-validation.md` (VAL-021) and `9-ai-classification.md`. **Assemble, do not invent.**
→ `DEP-039`, `CQ-069`.

### T41 | Session logs organised
```
Owner  you
Deps   T39
Output docs/sessions/ split by phase with a two-line index
Done   Opening any log at random looks deliberate
```
Gerben said logs are useful but will not be read line by line. That means sampled.

### T42 | Rehearse the narrative
```
Owner  you
Deps   T40, T41
Done   The Part C story told out loud, timed, under 20 minutes
```
Structure: problem and scope → what was cut → how work was split into specs with verifiable done
conditions → how agents were run against file boundaries → **where you stopped trusting the output
and rewrote it** → what comes next.

Find that last one in the logs now and note where it lives. One concrete moment beats twenty minutes
of generalities.

---

## Parallelisation

**T-P8.**

| Wave | Concurrent |
|---|---|
| 1 | T01 → T02 → T43 → T03 → T04 (serial, one agent) |
| 2 | **A:** T06–T12 · **D:** T13–T16 → T44 · **C:** T26 |
| 3 | **B:** T17 → T18, T19 → T20, T21 → T22 → T23 → T25 · **D:** T24 |
| 4 | **C:** T27–T30 |
| 5 | you: T31–T34 |
| 6 | T35 → T36 → T37 → T38 |
| 7 | T39–T42 |

Wave 2 is the widest: three agents, zero shared files. That is the concrete answer to "how did you
run agents in parallel" — the boundaries came from the spec (`ARC-028`), not from hope.

## Rules while running

- **T-P9. One ticket, one unit of work, roughly one file.** An agent that writes 400 lines produces a
  diff you will not read properly. This is also how the review budget in T33 stays realistic.
- **T-P10. Tests before implementation on every A-owned ticket.** The red test is the agent's done
  condition. Without it, the agent decides for itself when it is finished. → `CQ-070`.
- **T-P11. Commit per ticket**, and the message is **one line**:

  ```
  <type>(<domain>): <what was done, one or two sentences> [<ticket>]
  ```

  `type` is `feat`, `fix`, `docs`, `chore`, `test` or `refactor`. `domain` is the area touched —
  `simulation`, `applications`, `documents`, `auth`, `core`, `infra`, `specs`. Cite requirement ids
  when they add information.

  ```
  feat(simulation): actuarial monthly rate conversion, not I/12 [T06] — SIM-001, AC-002
  feat(applications): derived document checklist with per-row reasons [T12] — DOC-005..DOC-011
  ```

  **A body is the exception, not the default.** Add one only for a decision a reader cannot
  reconstruct from the diff — a spec correction, or a trade-off with a live alternative — and keep
  it to a few lines. A commit message that runs to twenty lines is a design note filed in the wrong
  place: it belongs in the spec it corrects or in `docs/sessions/`, where it can be found later.
  The history is read during the walkthrough by scrolling `git log --oneline`, and that view shows
  the subject only.
- **T-P12. Nothing merges with a failing lint or a failing `mypy --strict`.** Done means green, not
  "it runs". → `CQ-079`.
- **T-P13. If a ticket needs to edit a file it does not own, stop.** That is a boundary error: either
  the plan is wrong or the agent has drifted. Fix the boundary, do not work around it. → `ARC-009`,
  `ARC-015`.

---

# Appendix A — Ticket index

Source: `12-implementation.md`, superseded by this document.

| Phase | Tickets | Owner(s) |
|---|---|---|
| P0 Deploy skeleton | T01 – T05, T43 | D |
| P1 Domain core and platform | T06 – T16, T44 | A, D |
| P2 API surface | T17 – T25 | B, D |
| P3 Frontend | T26 – T30 | C |
| P4 Integration | T31 – T34 | you |
| P5 AI classification | T35 – T38 | A, B, C |
| P6 Ship | T39 – T42 | you |

Principles and standing rules carry `T-P` ids: `T-P1` – `T-P3` (principles), `T-P4` – `T-P6`
(coverage policy), `T-P7` (time budget), `T-P8` (parallelisation), `T-P9` – `T-P13` (rules while
running).

# Appendix B — Corrections against the source

| Item | Resolution |
|---|---|
| The source's Tier 1 coverage command names four pure modules | **`file_type.py` added**, making five. `ARC-008` lists it as a pure module and the Tier 1 rationale — pure, finite branches, being wrong is unrecoverable — describes the magic-byte check exactly. It is also a security control (`VAL-022`), which is the last place to leave a coverage hole. |
| T19 listed `app/core/dependencies.py` among its files | **`app/domains/auth/dependencies.py`.** `core` may not import a domain (`ARC-012`); `ARC-042` made the auth dependency module a second declared public surface for exactly this reason. |
| `classification/evaluator.py` | Kept as the source names it. `2-architecture.md` and `9-ai-classification.md` had `evaluate.py` — my invention from the function name — and were corrected to match: the module is a noun beside `calculator.py` and `state_machine.py`, the function inside stays `evaluate()`. |
| `00-scope.md`, `02-simulation.md`, `03-code-quality.md`, `04-architecture.md`, `05-ui.md`, `07-deployment.md`, `08-auth.md`, `09-validation.md`, `11-ai-classification.md` | Rewritten to this repo's numbering, with the specific rule ids added so each ticket points at what it implements |
| T02 did not create a linter configuration | `pyproject.toml` added to its files and to its done condition. Nothing in any spec said where the CQ-076 rule set lived, so `ruff check` would have run defaults and T34 would have gone green having checked almost nothing. |
| T10 named `SimulationInput` with no spec defining it | `ARC-043` now separates the simulation entity types from the wire schemas; the ticket points at it. |
| T26 did not own the ESLint configuration | added to its files, same reasoning as T02. |

# Appendix C — Corrections made at the start of implementation

Six gaps found by reading the whole set against this plan before writing code. All of them are files
or checks that a spec required and no ticket produced.

| Gap | Resolution |
|---|---|
| `Makefile`, `.env.example`, `infra/docker-compose.yml`, `frontend/proxy.conf.json` had no owning ticket | **T43** |
| `tests/conftest.py` had no owning ticket, and three units need it | **T44**, before Sync point 1 |
| `observability/*` had no owning ticket | folded into T15, which already owns the instrumentation |
| The Angular scaffold had no owning ticket, and T03's build needs it | folded into T01 |
| `make lint` did not run the checks `UI-027` and `UI-064` claim it runs | added to `DEP-038`; T26 points at them |
| The UI-064 hex grep would have failed against the preset `UI-039` mandates | `UI-030` now names both token surfaces; the check excludes `theme/` |
| Five `core/` modules had no owning ticket | `health.py` and `dependencies.py` → **T02**, which is what creates `/health`; `enums.py` → **T06**, the first unit-A ticket and the only one that can write it before anything reads it; `rate_limit.py` and `limits.py` → **T14**, now *Errors, handlers and request guards* — both are request-level guards whose only output is a registry code |

`ARC-028` gave unit D all of `core/*`, but four tickets between them named only six of the thirteen
modules. Ownership at the unit level is not ownership at the file level, and `T-P2` needs the
second.

Four more found at the start of batch 2:

| Gap | Resolution |
|---|---|
| `/ready` had no owning ticket, though `DEP-037`, `DEP-040` and `DEP-050` all require it | **T16**, the earliest point where both stores it probes exist |
| `CQ-034`'s `save(key, ...)` contradicted `VAL-023` and this plan's own `test_save_returns_generated_key` | the backend generates the key; a caller that picks the key picks a path |
| `DEP-031` stated a denylist and an allowlist in three lines | the denylist is the rule — it is the only one enumerated anywhere |
| `UX-055` – `UX-061` and `UI-067` were enforced by a human at a 375px window | **Playwright as a gate** (UI-068, UX-062), installed in T26, scenarios named in T27 – T30 |
