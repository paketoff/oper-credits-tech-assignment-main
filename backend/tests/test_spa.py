"""The Angular shell is served for any route Angular itself owns. DEP-013, DEP-014."""


async def test_deep_route_returns_index_html(client):
    response = await client.get("/application/123")

    assert response.status_code == 200
    assert "<app-root>" in response.text


async def test_api_route_still_resolves(client):
    # DEP-013: mount order matters. A real API route must never fall through
    # to the catch-all, however late it is registered.
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_unknown_api_route_returns_404_not_index(client):
    # Without this guard the catch-all — which matches literally everything
    # not claimed by an earlier route — would serve the SPA shell with a 200
    # for a typo'd or removed API path.
    response = await client.get("/api/this-route-does-not-exist")

    assert response.status_code == 404
    assert "<app-root>" not in response.text


async def test_a_built_bundle_is_served_as_itself_not_as_the_shell(client):
    # The failure this exists for: Angular's application builder emits
    # `main-<hash>.js` at the root of the build output, not under `assets/`.
    # With only an `/assets` mount the bundle fell through to the catch-all
    # and every browser got `index.html` with a 200 and `text/html`, refused
    # it on the module MIME check, and rendered a blank page — in the
    # production container and on the deployed URL alike, while every test
    # here still passed.
    from app import main

    bundle = main._STATIC_DIR / "main-P4TEST.js"
    bundle.write_text("export const built = true;\n")
    try:
        response = await client.get("/main-P4TEST.js")
    finally:
        bundle.unlink()

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "<app-root>" not in response.text


async def test_a_path_escaping_the_static_root_falls_back_to_the_shell():
    # The catch-all takes an arbitrary URL path. A traversal must not read a
    # file outside the build output, and there is nothing to 404 on either —
    # to Angular it is simply a route it does not have.
    from pathlib import Path

    from app.core import spa

    assert spa._built_file(Path("/tmp"), "../etc/passwd") is None
