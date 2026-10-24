from httpx import AsyncClient

from tests.fakes import FakeIdentityProvider
from tests.helpers import API, auth, create_product, place, register


async def join(client: AsyncClient, owner: str, courier: str) -> dict:
    invite = (await client.post(f"{API}/courier-invites", headers=auth(owner))).json()
    response = await client.post(
        f"{API}/courier-invites/{invite['token']}/accept",
        json={"name": "João Entregas", "phone": "11955554444"},
        headers=auth(courier),
    )
    assert response.status_code == 200, response.text
    return {**response.json(), "token": invite["token"], "url": invite["url"]}


async def test_invite_link_is_single_use(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    owner, body = await register(client, identity, "owner-1")
    courier = identity.add_user("courier-1")
    other = identity.add_user("courier-2")

    membership = await join(client, owner, courier)
    reused = await client.post(
        f"{API}/courier-invites/{membership['token']}/accept",
        json={"name": "Outro"},
        headers=auth(other),
    )
    public = await client.get(f"{API}/courier-invites/{membership['token']}")

    assert membership["url"].endswith(f"/entregador/convite/{membership['token']}")
    assert membership["establishment_slug"] == body["slug"]
    assert (reused.status_code, public.status_code) == (404, 404)


async def test_owner_cannot_join_own_establishment(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    owner, _ = await register(client, identity, "owner-1")
    invite = (await client.post(f"{API}/courier-invites", headers=auth(owner))).json()

    described = await client.get(f"{API}/courier-invites/{invite['token']}")
    response = await client.post(
        f"{API}/courier-invites/{invite['token']}/accept",
        json={"name": "Dono"},
        headers=auth(owner),
    )

    assert described.json()["establishment_name"] == "Brabos Burguer"
    assert response.status_code == 409


async def test_courier_delivers_accepted_orders(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    owner, body = await register(client, identity, "owner-1")
    other_owner, other_body = await register(client, identity, "owner-2")
    courier = identity.add_user("courier-1")
    membership = await join(client, owner, courier)
    product = await create_product(client, owner)
    other_product = await create_product(client, other_owner)
    pending = await place(client, body["slug"], [{"product_id": product["id"]}])
    ready = await place(client, body["slug"], [{"product_id": product["id"]}])
    foreign = await place(client, other_body["slug"], [{"product_id": other_product["id"]}])
    await client.post(f"{API}/orders/{ready['id']}/accept", headers=auth(owner))
    await client.post(f"{API}/orders/{foreign['id']}/accept", headers=auth(other_owner))

    queue = await client.get(f"{API}/courier/orders", headers=auth(courier))
    not_ready = await client.post(
        f"{API}/courier/orders/{pending['id']}/deliver", headers=auth(courier)
    )
    not_mine = await client.post(
        f"{API}/courier/orders/{foreign['id']}/deliver", headers=auth(courier)
    )
    delivered = await client.post(
        f"{API}/courier/orders/{ready['id']}/deliver", headers=auth(courier)
    )
    events = await client.get(
        f"{API}/order-events", params={"order_id": ready["id"]}, headers=auth(owner)
    )

    assert [order["id"] for order in queue.json()["items"]] == [ready["id"]]
    assert (not_ready.status_code, not_mine.status_code) == (409, 404)
    assert delivered.json()["status"] == "delivered"
    assert delivered.json()["courier_id"] == membership["courier_id"]
    assert events.json()["items"][0]["actor"] == "courier"


async def test_deactivated_courier_loses_access(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    owner, _ = await register(client, identity, "owner-1")
    courier = identity.add_user("courier-1")
    membership = await join(client, owner, courier)

    listed = await client.get(f"{API}/couriers", headers=auth(owner))
    await client.patch(
        f"{API}/couriers/{membership['courier_id']}", json={"active": False}, headers=auth(owner)
    )
    memberships = await client.get(f"{API}/courier/me", headers=auth(courier))
    deleted = await client.delete(f"{API}/couriers/{membership['courier_id']}", headers=auth(owner))

    assert listed.json()["items"][0]["name"] == "João Entregas"
    assert memberships.json() == []
    assert deleted.status_code == 204
