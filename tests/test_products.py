from httpx import AsyncClient

from tests.fakes import FakeIdentityProvider, FakeIntegrations, FakeObjectStorage, signed
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
    prefix = f"establishments/{body['id']}/products"
    first_key, second_key, third_key = (f"{prefix}/{name}.webp" for name in "abc")

    unconfigured = await client.patch(url, json={"image_keys": [first_key]}, headers=auth(token))
    integrations.storage = storage = FakeObjectStorage()
    foreign = await client.patch(
        url, json={"image_keys": ["establishments/other/products/a.webp"]}, headers=auth(token)
    )
    first = await client.patch(
        url, json={"image_keys": [first_key, second_key]}, headers=auth(token)
    )
    replaced = await client.patch(
        url, json={"image_keys": [second_key, third_key]}, headers=auth(token)
    )
    cleared = await client.patch(url, json={"image_keys": []}, headers=auth(token))

    assert (unconfigured.status_code, foreign.status_code) == (422, 422)
    assert first.json()["image_url"] == signed(first_key)
    assert first.json()["image_urls"] == [signed(key) for key in (first_key, second_key)]
    assert replaced.json()["image_url"] == signed(second_key)
    assert replaced.status_code == cleared.status_code == 200
    assert cleared.json()["image_url"] is None and cleared.json()["image_urls"] == []
    assert storage.deleted == [first_key, second_key, third_key]


async def test_product_images_are_limited_and_unique(
    client: AsyncClient, identity: FakeIdentityProvider, integrations: FakeIntegrations
) -> None:
    token, body = await register(client, identity, "owner-1")
    integrations.storage = FakeObjectStorage()
    keys = [f"establishments/{body['id']}/products/{index}.webp" for index in range(6)]

    too_many = await client.post(
        f"{API}/products", json={"name": "A", "price": 1, "image_keys": keys}, headers=auth(token)
    )
    repeated = await client.post(
        f"{API}/products",
        json={"name": "A", "price": 1, "image_keys": [keys[0], keys[0]]},
        headers=auth(token),
    )
    five = await create_product(client, token, "B", image_keys=keys[:5])

    assert (too_many.status_code, repeated.status_code) == (422, 422)
    assert len(five["image_urls"]) == 5


async def test_only_three_products_can_be_featured(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1")
    combos = [await create_product(client, token, f"Combo {n}", featured=True) for n in range(3)]
    extra = await create_product(client, token, "Extra")

    blocked = await client.patch(
        f"{API}/products/{extra['id']}", json={"featured": True}, headers=auth(token)
    )
    blocked_create = await client.post(
        f"{API}/products",
        json={"name": "Outro", "price": 1, "featured": True},
        headers=auth(token),
    )
    again = await client.patch(
        f"{API}/products/{combos[0]['id']}", json={"featured": True}, headers=auth(token)
    )
    released = await client.patch(
        f"{API}/products/{combos[0]['id']}", json={"featured": False}, headers=auth(token)
    )
    swapped = await client.patch(
        f"{API}/products/{extra['id']}", json={"featured": True}, headers=auth(token)
    )
    public = await client.get(f"{API}/establishments/{body['slug']}/products")

    assert (blocked.status_code, blocked_create.status_code) == (409, 409)
    assert (again.status_code, released.status_code, swapped.status_code) == (200, 200, 200)
    assert sorted(item["name"] for item in public.json()["items"] if item["featured"]) == [
        "Combo 1",
        "Combo 2",
        "Extra",
    ]


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
    assert upload.json()["view_url"] == signed(key)
    assert "public_url" not in upload.json()
    product = await create_product(client, token, image_keys=[key])
    assert product["image_url"] == signed(key)
