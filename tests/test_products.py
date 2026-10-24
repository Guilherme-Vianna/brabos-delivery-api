from httpx import AsyncClient

from tests.fakes import FakeIdentityProvider, FakeIntegrations, FakeObjectStorage
from tests.helpers import API, auth, create_product, place, register


async def test_create_and_list_products(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1")
    burger = await create_product(
        client,
        token,
        "  X-Bacon ",
        32.9,
        category="Lanches",
        ingredients="Pão, carne, bacon",
        allows_half=True,
        asks_doneness=True,
    )
    await create_product(client, token, "Coca-Cola", 7, category="Bebidas", active=False)

    owner = await client.get(f"{API}/products", headers=auth(token))
    public = await client.get(f"{API}/establishments/{body['slug']}/products")

    assert (burger["name"], burger["price"], burger["image_url"]) == ("X-Bacon", 32.9, None)
    assert owner.json()["total"] == 2
    assert [item["name"] for item in public.json()["items"]] == ["X-Bacon"]
    assert "active" not in public.json()["items"][0]


async def test_product_names_are_unique_ignoring_case(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, _ = await register(client, identity, "owner-1")
    other, _ = await register(client, identity, "owner-2")
    await create_product(client, token, "X-Tudo")

    duplicate = await client.post(
        f"{API}/products", json={"name": "x-tudo", "price": 1}, headers=auth(token)
    )
    elsewhere = await client.post(
        f"{API}/products", json={"name": "X-Tudo", "price": 1}, headers=auth(other)
    )

    assert (duplicate.status_code, elsewhere.status_code) == (409, 201)


async def test_owner_requires_establishment_and_cannot_touch_others(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, _ = await register(client, identity, "owner-1")
    other, _ = await register(client, identity, "owner-2")
    stranger = identity.add_user("stranger")
    product = await create_product(client, token)

    forbidden = await client.get(f"{API}/products", headers=auth(stranger))
    hidden = await client.patch(
        f"{API}/products/{product['id']}", json={"price": 1}, headers=auth(other)
    )

    assert (forbidden.status_code, hidden.status_code) == (403, 404)


async def test_used_products_cannot_be_deleted(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1")
    used = await create_product(client, token, "X-Burguer")
    unused = await create_product(client, token, "X-Salada")
    order = await place(client, body["slug"], [{"product_id": used["id"]}])

    blocked = await client.delete(f"{API}/products/{used['id']}", headers=auth(token))
    deleted = await client.delete(f"{API}/products/{unused['id']}", headers=auth(token))
    await client.patch(f"{API}/products/{used['id']}", json={"price": 99}, headers=auth(token))
    detail = await client.get(f"{API}/orders/{order['id']}", headers=auth(token))

    assert (blocked.status_code, deleted.status_code) == (409, 204)
    assert detail.json()["items"][0]["unit_price"] == 30


async def test_product_images_need_storage_and_own_prefix(
    client: AsyncClient, identity: FakeIdentityProvider, integrations: FakeIntegrations
) -> None:
    token, body = await register(client, identity, "owner-1")
    product = await create_product(client, token)
    url = f"{API}/products/{product['id']}"
    own_key = f"establishments/{body['id']}/products/a.webp"

    unconfigured = await client.patch(url, json={"image_key": own_key}, headers=auth(token))
    integrations.storage = storage = FakeObjectStorage()
    foreign = await client.patch(
        url, json={"image_key": "establishments/other/products/a.webp"}, headers=auth(token)
    )
    first = await client.patch(url, json={"image_key": own_key}, headers=auth(token))
    replaced = await client.patch(
        url, json={"image_key": own_key.replace("a.webp", "b.webp")}, headers=auth(token)
    )
    cleared = await client.patch(url, json={"image_key": None}, headers=auth(token))

    assert (unconfigured.status_code, foreign.status_code) == (422, 422)
    assert first.json()["image_url"] == f"https://cdn.test/{own_key}"
    assert replaced.status_code == cleared.status_code == 200
    assert cleared.json()["image_url"] is None
    assert storage.deleted == [own_key, own_key.replace("a.webp", "b.webp")]


async def test_uploads_return_presigned_urls(
    client: AsyncClient, identity: FakeIdentityProvider, integrations: FakeIntegrations
) -> None:
    token, body = await register(client, identity, "owner-1")
    payload = {"kind": "product", "content_type": "image/webp", "size": 1024}

    unconfigured = await client.post(f"{API}/uploads", json=payload, headers=auth(token))
    integrations.storage = FakeObjectStorage()
    too_big = await client.post(
        f"{API}/uploads", json={**payload, "size": 6 * 1024 * 1024}, headers=auth(token)
    )
    wrong_type = await client.post(
        f"{API}/uploads", json={**payload, "content_type": "image/gif"}, headers=auth(token)
    )
    upload = await client.post(f"{API}/uploads", json=payload, headers=auth(token))

    assert unconfigured.status_code == 503
    assert (too_big.status_code, wrong_type.status_code) == (422, 422)
    key = upload.json()["key"]
    assert key.startswith(f"establishments/{body['id']}/products/") and key.endswith(".webp")
    assert upload.json()["method"] == "PUT"
    product = await create_product(client, token, image_key=key)
    assert product["image_url"] == f"https://cdn.test/{key}"
