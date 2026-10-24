from httpx import AsyncClient

from tests.fakes import FakeIdentityProvider
from tests.helpers import API, auth, create_product, place, register, update_establishment


async def test_sales_report(client: AsyncClient, identity: FakeIdentityProvider) -> None:
    token, body = await register(client, identity, "owner-1")
    await update_establishment(client, token, delivery_fee_enabled=True, delivery_fee=5)
    bacon = await create_product(client, token, "X-Bacon", 40, allows_half=True)
    salad = await create_product(client, token, "X-Salada", 30, allows_half=True)
    slug = body["slug"]

    await place(
        client,
        slug,
        [{"product_id": bacon["id"], "half_product_id": salad["id"]}],
        payment_method="cash",
    )
    await place(client, slug, [{"product_id": salad["id"], "quantity": 2}])
    cancelled = await place(client, slug, [{"product_id": bacon["id"]}])
    await client.post(
        f"{API}/orders/{cancelled['id']}/cancel", json={"reason": "Teste"}, headers=auth(token)
    )

    report = (await client.get(f"{API}/reports/sales", headers=auth(token))).json()

    assert (report["orders"], report["revenue"], report["average_ticket"]) == (2, 110, 55)
    assert (report["delivery_fees"], report["cancelled_orders"], report["cancelled_value"]) == (
        10,
        1,
        45,
    )
    assert [(p["name"], p["quantity"], p["revenue"]) for p in report["top_products"]] == [
        ("X-Salada", 2.5, 80),
        ("X-Bacon", 0.5, 20),
    ]
    assert {item["method"]: item["orders"] for item in report["by_payment_method"]} == {
        "pix": 1,
        "cash": 1,
    }
    assert sum(day["orders"] for day in report["by_day"]) == 2


async def test_audit_lists_history_of_the_establishment(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1")
    other, _ = await register(client, identity, "owner-2")
    product = await create_product(client, token)
    await create_product(client, other)
    await client.patch(f"{API}/products/{product['id']}", json={"price": 31}, headers=auth(token))
    order = await place(client, body["slug"], [{"product_id": product["id"]}])

    products = await client.get(f"{API}/audit", params={"entity": "products"}, headers=auth(token))
    everything = await client.get(f"{API}/audit", params={"limit": 100}, headers=auth(token))
    unknown = await client.get(f"{API}/audit", params={"entity": "users"}, headers=auth(token))

    entries = products.json()["items"]
    assert [(e["operation"], e["snapshot"]["price"]) for e in entries] == [
        ("update", 31),
        ("insert", 30),
    ]
    assert entries[0]["changed_by"] == "owner-1"
    entities = {entry["entity"] for entry in everything.json()["items"]}
    assert {"establishments", "products", "orders", "order_items", "opening_hours"} <= entities
    order_entry = next(e for e in everything.json()["items"] if e["entity_id"] == order["id"])
    assert order_entry["changed_by"] is None
    assert "customer_token_hash" not in order_entry["snapshot"]
    assert unknown.status_code == 422
