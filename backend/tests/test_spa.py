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
