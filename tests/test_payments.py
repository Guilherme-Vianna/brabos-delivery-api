import json

from httpx import AsyncClient

from tests.fakes import FakeIdentityProvider, FakeIntegrations, FakePaymentGateway
from tests.helpers import (
    API,
    auth,
    create_product,
    customer,
    order_payload,
    register,
    register_push,
    update_establishment,
)


async def webhook(client: AsyncClient, signature: str = "valid", **data: str) -> int:
    response = await client.post(
        f"{API}/payments/webhook",
        content=json.dumps(data),
        headers={"Stripe-Signature": signature},
    )
    return response.status_code


async def online_setup(
    client: AsyncClient, identity: FakeIdentityProvider, integrations: FakeIntegrations
) -> tuple[str, dict, dict, FakePaymentGateway]:
    integrations.gateway = gateway = FakePaymentGateway()
    token, body = await register(client, identity, "owner-1")
    await update_establishment(
        client, token, online_payments_enabled=True, delivery_fee_enabled=True, delivery_fee=4
    )
    product = await create_product(client, token)
    return token, body, product, gateway


async def place_online(client: AsyncClient, slug: str, product: dict) -> dict:
    response = await client.post(
        f"{API}/establishments/{slug}/orders",
        json=order_payload([{"product_id": product["id"]}], payment_method="online"),
        headers=customer(),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_online_payment_requires_configuration(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1")
    product = await create_product(client, token)

    order = await client.post(
        f"{API}/establishments/{body['slug']}/orders",
        json=order_payload([{"product_id": product["id"]}], payment_method="online"),
        headers=customer(),
    )
    hook = await webhook(client, kind="paid")

    assert (order.status_code, hook) == (422, 503)


async def test_paid_webhook_releases_order(
    client: AsyncClient, identity: FakeIdentityProvider, integrations: FakeIntegrations
) -> None:
    token, body, product, gateway = await online_setup(client, identity, integrations)
    await register_push(client, "owner", "owner-fcm-token-000001", auth(token))

    order = await place_online(client, body["slug"], product)
    blocked = await client.post(f"{API}/orders/{order['id']}/accept", headers=auth(token))
    invalid = await webhook(client, "forged", kind="paid", order_id=order["id"])
    paid = await webhook(client, kind="paid", order_id=order["id"], payment_reference="pi_1")
    replay = await webhook(client, kind="paid", order_id=order["id"], payment_reference="pi_1")
    accepted = await client.post(f"{API}/orders/{order['id']}/accept", headers=auth(token))

    assert order["checkout_url"] == f"https://pay.test/{order['id']}"
    assert order["payment_status"] == "pending"
    assert [(line.name, line.quantity) for line in gateway.checkouts[0][1]] == [
        ("X-Burguer", 1),
        ("Taxa de entrega", 1),
    ]
    assert blocked.status_code == 409
    assert (invalid, paid, replay) == (422, 204, 204)
    assert accepted.json()["payment_status"] == "paid"
    assert integrations.push.titles_for("owner-fcm-token-000001") == ["Novo pedido #1"]


async def test_expired_checkout_cancels_order(
    client: AsyncClient, identity: FakeIdentityProvider, integrations: FakeIntegrations
) -> None:
    token, body, product, _ = await online_setup(client, identity, integrations)
    order = await place_online(client, body["slug"], product)

    await webhook(client, kind="expired", checkout_reference=f"cs_{order['id'].replace('-', '')}")
    detail = await client.get(f"{API}/orders/{order['id']}", headers=auth(token))

    assert (detail.json()["status"], detail.json()["cancelled_by"]) == ("cancelled", "system")


async def test_cancelling_paid_order_refunds(
    client: AsyncClient, identity: FakeIdentityProvider, integrations: FakeIntegrations
) -> None:
    token, body, product, gateway = await online_setup(client, identity, integrations)
    order = await place_online(client, body["slug"], product)
    await webhook(client, kind="paid", order_id=order["id"], payment_reference="pi_9")

    cancelled = await client.post(
        f"{API}/orders/{order['id']}/cancel", json={"reason": "Acabou o pão"}, headers=auth(token)
    )
    events = await client.get(
        f"{API}/order-events", params={"order_id": order["id"]}, headers=auth(token)
    )

    assert cancelled.json()["payment_status"] == "refunded"
    assert gateway.refunds == ["pi_9"]
    assert [event["kind"] for event in events.json()["items"]] == [
        "refunded",
        "cancelled",
        "paid",
        "placed",
    ]
