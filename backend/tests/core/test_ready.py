"""Readiness probes both stores, and answers in its own shape. DEP-037, API-069."""

import pytest

from app.core.dependencies import get_storage
from app.core.storage import LocalStorage


async def test_ready_returns_ready_when_both_stores_are_usable(client, blob_dir):
    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_ready_returns_503_when_the_blob_directory_is_unwritable(app, client, tmp_path):
    # VAL-020: "/data unwritable -> /ready returns 503". Simulated by pointing
    # the backend at a path it cannot create, which is what a bad volume mount
    # looks like from inside the process.
    unwritable = tmp_path / "not-a-directory"
    unwritable.write_bytes(b"this is a file, so mkdir under it fails")
    app.dependency_overrides[get_storage] = lambda: LocalStorage(unwritable / "blobs")

    response = await client.get("/ready")
    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


async def test_a_failed_probe_answers_in_the_probe_shape_not_the_error_shape(app, client, tmp_path):
    # API-069: /health and /ready are the only carve-out from the {code,
    # message, field} contract, because they sit outside /api and their reader
    # is a health checker rather than a client.
    unwritable = tmp_path / "blocked"
    unwritable.write_bytes(b"")
    app.dependency_overrides[get_storage] = lambda: LocalStorage(unwritable / "blobs")

    body = (await client.get("/ready")).json()
    app.dependency_overrides.clear()

    assert set(body) == {"status"}
    assert "code" not in body


async def test_liveness_does_not_depend_on_the_stores(app, client, tmp_path):
    # DEP-036. A liveness probe that fails when storage is busy makes the
    # platform restart a machine that was working.
    unwritable = tmp_path / "blocked-too"
    unwritable.write_bytes(b"")
    app.dependency_overrides[get_storage] = lambda: LocalStorage(unwritable / "blobs")

    response = await client.get("/health")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/health", "/ready"])
async def test_probes_carry_a_request_id(client, blob_dir, path):
    response = await client.get(path)

    assert response.headers["X-Request-ID"]
