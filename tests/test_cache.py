from httpx import AsyncClient

from tests.fakes import FakeIdentityProvider
from tests.helpers import API, auth, create_product, register


async def test_owner_reads_are_cached_and_invalidated(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, _ = await register(client, identity, "owner-1")
    await create_product(client, token)

    first = await client.get(f"{API}/products", headers=auth(token))
    second = await client.get(f"{API}/products", headers=auth(token))
    await create_product(client, token, "X-Egg")
    third = await client.get(f"{API}/products", headers=auth(token))

    assert "x-cache" not in first.headers
    assert second.headers["x-cache"] == "HIT"
    assert "x-cache" not in third.headers
    assert third.json()["total"] == 2


async def test_public_menu_is_cached_per_slug(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1")
    await create_product(client, token)
    url = f"{API}/establishments/{body['slug']}/products"

    await client.get(url)
    cached = await client.get(url)
    await client.patch(
        f"{API}/products/{cached.json()['items'][0]['id']}",
        json={"active": False},
        headers=auth(token),
    )
    refreshed = await client.get(url)

    assert cached.headers["x-cache"] == "HIT"
    assert refreshed.json()["total"] == 0
