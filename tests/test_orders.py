import asyncio

from httpx import AsyncClient

from tests.fakes import FakeIdentityProvider, FakeIntegrations
from tests.helpers import (
    API,
    auth,
    create_product,
    customer,
    order_payload,
    place,
    register,
    register_push,
    set_hours,
    update_establishment,
)


async def menu(client: AsyncClient, token: str) -> dict[str, dict]:
    return {
        "bacon": await create_product(
            client, token, "X-Bacon", 35, allows_half=True, asks_doneness=True
        ),
        "salad": await create_product(client, token, "X-Salada", 28, allows_half=True),
        "soda": await create_product(client, token, "Refrigerante", 6.5),
    }


async def test_half_and_half_charges_the_most_expensive_half(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1")
    products = await menu(client, token)
    await update_establishment(client, token, delivery_fee_enabled=True, delivery_fee=5)

    order = await place(
        client,
        body["slug"],
        [
            {
                "product_id": products["salad"]["id"],
                "half_product_id": products["bacon"]["id"],
                "doneness": "medium",
                "quantity": 2,
            },
            {"product_id": products["soda"]["id"], "notes": "Bem gelado"},
        ],
        payment_method="cash",
        change_for=100,
    )

    half, soda = order["items"]
    assert (half["unit_price"], half["line_total"], half["half_product_name"]) == (
        35,
        70,
        "X-Bacon",
    )
    assert soda["notes"] == "Bem gelado"
    assert (order["subtotal"], order["delivery_fee"], order["total"]) == (76.5, 5, 81.5)
    assert (order["status"], order["number"], order["change_for"]) == ("placed", 1, 100)
    assert order["payment_status"] == "not_required"


async def test_order_validation_rules(client: AsyncClient, identity: FakeIdentityProvider) -> None:
    token, body = await register(client, identity, "owner-1")
    products = await menu(client, token)
    await update_establishment(client, token, min_order=10)
    url = f"{API}/establishments/{body['slug']}/orders"
    bacon, salad, soda = products["bacon"]["id"], products["salad"]["id"], products["soda"]["id"]

    cases = [
        [{"product_id": bacon}],
        [{"product_id": soda, "doneness": "rare"}],
        [{"product_id": soda, "half_product_id": salad}],
        [{"product_id": salad, "half_product_id": salad}],
        [{"product_id": soda}],
    ]
    for items in cases:
        response = await client.post(url, json=order_payload(items), headers=customer())
        assert response.status_code == 422, items
    low_change = await client.post(
        url,
        json=order_payload([{"product_id": salad}], payment_method="cash", change_for=20),
        headers=customer(),
    )
    pix_change = await client.post(
        url, json=order_payload([{"product_id": salad}], change_for=50), headers=customer()
    )
    no_token = await client.post(url, json=order_payload([{"product_id": salad}]))

    assert (low_change.status_code, pix_change.status_code, no_token.status_code) == (
        422,
        422,
        422,
    )


async def test_inactive_products_cannot_be_ordered(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1")
    product = await create_product(client, token, active=False)

    response = await client.post(
        f"{API}/establishments/{body['slug']}/orders",
        json=order_payload([{"product_id": product["id"]}]),
        headers=customer(),
    )

    assert response.status_code == 422


async def test_closed_establishment_rejects_orders(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1", open_now=False)
    product = await create_product(client, token)
    await set_hours(client, token, [])

    response = await client.post(
        f"{API}/establishments/{body['slug']}/orders",
        json=order_payload([{"product_id": product["id"]}]),
        headers=customer(),
    )

    assert response.status_code == 409


async def test_order_numbers_are_sequential_under_concurrency(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1")
    product = await create_product(client, token)

    orders = await asyncio.gather(
        *(place(client, body["slug"], [{"product_id": product["id"]}]) for _ in range(5))
    )

    assert sorted(order["number"] for order in orders) == [1, 2, 3, 4, 5]


async def test_owner_flow_and_events(client: AsyncClient, identity: FakeIdentityProvider) -> None:
    token, body = await register(client, identity, "owner-1")
    product = await create_product(client, token)
    order = await place(client, body["slug"], [{"product_id": product["id"]}])
    url = f"{API}/orders/{order['id']}"

    early_delivery = await client.post(f"{url}/deliver", headers=auth(token))
    accepted = await client.post(f"{url}/accept", headers=auth(token))
    accepted_twice = await client.post(f"{url}/accept", headers=auth(token))
    delivered = await client.post(f"{url}/deliver", headers=auth(token))
    late_cancel = await client.post(
        f"{url}/cancel", json={"reason": "Cliente desistiu"}, headers=auth(token)
    )
    events = await client.get(f"{API}/order-events", headers=auth(token))
    filtered = await client.get(
        f"{API}/orders", params={"status": "delivered"}, headers=auth(token)
    )

    assert (early_delivery.status_code, accepted_twice.status_code) == (409, 409)
    assert accepted.json()["status"] == "accepted" and accepted.json()["accepted_at"]
    assert delivered.json()["status"] == "delivered"
    assert late_cancel.status_code == 409
    assert [event["kind"] for event in events.json()["items"]] == [
        "delivered",
        "accepted",
        "placed",
    ]
    assert events.json()["items"][0]["actor"] == "owner"
    assert filtered.json()["total"] == 1


async def test_owner_cancel_requires_reason(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1")
    product = await create_product(client, token)
    order = await place(client, body["slug"], [{"product_id": product["id"]}])
    url = f"{API}/orders/{order['id']}/cancel"

    missing = await client.post(url, json={}, headers=auth(token))
    cancelled = await client.post(url, json={"reason": "Sem pão"}, headers=auth(token))

    assert missing.status_code == 422
    assert (cancelled.json()["status"], cancelled.json()["cancel_reason"]) == (
        "cancelled",
        "Sem pão",
    )
    assert cancelled.json()["cancelled_by"] == "owner"


async def test_auto_accept(client: AsyncClient, identity: FakeIdentityProvider) -> None:
    token, body = await register(client, identity, "owner-1")
    await update_establishment(client, token, auto_accept=True)
    product = await create_product(client, token)

    order = await place(client, body["slug"], [{"product_id": product["id"]}])

    assert order["status"] == "accepted"


async def test_customer_tracks_and_cancels_with_device_token(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1")
    product = await create_product(client, token)
    device = "d" * 40
    order = await place(client, body["slug"], [{"product_id": product["id"]}], device=device)
    second = await place(client, body["slug"], [{"product_id": product["id"]}], device=device)
    base = f"{API}/establishments/{body['slug']}/my-orders"

    mine = await client.get(f"{base}/{order['id']}", headers=customer(device))
    stranger = await client.get(f"{base}/{order['id']}", headers=customer())
    listing = await client.get(base, headers=customer(device))
    cancelled = await client.post(f"{base}/{order['id']}/cancel", json={}, headers=customer(device))
    await client.post(f"{API}/orders/{second['id']}/accept", headers=auth(token))
    too_late = await client.post(f"{base}/{second['id']}/cancel", json={}, headers=customer(device))

    assert mine.status_code == 200 and stranger.status_code == 404
    assert listing.json()["total"] == 2
    assert (cancelled.json()["status"], cancelled.json()["cancelled_by"]) == (
        "cancelled",
        "customer",
    )
    assert too_late.status_code == 409


async def test_signed_in_customer_sees_orders_from_any_device(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1")
    product = await create_product(client, token)
    customer_token = identity.add_user("customer-1")
    order = await place(
        client, body["slug"], [{"product_id": product["id"]}], headers=auth(customer_token)
    )

    other_device = await client.get(
        f"{API}/establishments/{body['slug']}/my-orders/{order['id']}",
        headers={**customer(), **auth(customer_token)},
    )
    history = await client.get(f"{API}/customers/me/orders", headers=auth(customer_token))

    assert other_device.status_code == 200
    assert history.json()["items"][0]["establishment_slug"] == body["slug"]


async def test_push_notifications_follow_the_order(
    client: AsyncClient, identity: FakeIdentityProvider, integrations: FakeIntegrations
) -> None:
    token, body = await register(client, identity, "owner-1")
    courier_token = identity.add_user("courier-1")
    invite = (await client.post(f"{API}/courier-invites", headers=auth(token))).json()
    await client.post(
        f"{API}/courier-invites/{invite['token']}/accept",
        json={"name": "Moto Boy"},
        headers=auth(courier_token),
    )
    product = await create_product(client, token)
    device = "c" * 40
    await register_push(client, "owner", "owner-fcm-token-000001", auth(token))
    await register_push(client, "courier", "courier-fcm-token-0001", auth(courier_token))
    await register_push(client, "customer", "customer-fcm-token-001", customer(device))
    integrations.push.invalid.add("courier-fcm-token-0001")

    order = await place(client, body["slug"], [{"product_id": product["id"]}], device=device)
    await client.post(f"{API}/orders/{order['id']}/accept", headers=auth(token))
    await client.post(f"{API}/orders/{order['id']}/deliver", headers=auth(token))
    second = await place(client, body["slug"], [{"product_id": product["id"]}], device=device)
    await client.post(f"{API}/orders/{second['id']}/accept", headers=auth(token))

    push = integrations.push
    assert push.titles_for("owner-fcm-token-000001") == ["Novo pedido #1", "Novo pedido #2"]
    assert push.titles_for("customer-fcm-token-001") == [
        "Pedido aceito",
        "Pedido entregue",
        "Pedido aceito",
    ]
    assert push.titles_for("courier-fcm-token-0001") == [f"Entrega disponível · {body['name']}"]


async def test_push_registration_rules(client: AsyncClient, identity: FakeIdentityProvider) -> None:
    stranger = identity.add_user("stranger")
    url = f"{API}/push-devices"
    fcm = "x" * 30

    anonymous = await client.post(url, json={"fcm_token": fcm, "role": "customer"})
    owner = await client.post(url, json={"fcm_token": fcm, "role": "owner"}, headers=auth(stranger))
    courier = await client.post(
        url, json={"fcm_token": fcm, "role": "courier"}, headers=auth(stranger)
    )

    assert (anonymous.status_code, owner.status_code, courier.status_code) == (401, 403, 403)
