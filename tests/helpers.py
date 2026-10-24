from typing import Any
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.fakes import FakeIdentityProvider

API = "/api/v1"
ALL_DAY = [{"weekday": day, "opens_at": "06:00", "closes_at": "05:59"} for day in range(7)]
VALID_CNPJ = "11222333000181"


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def customer(token: str | None = None) -> dict[str, str]:
    return {"X-Customer-Token": token or uuid4().hex + uuid4().hex}


def establishment_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "name": "Brabos Burguer",
        "address": "Rua das Flores, 100 - Centro",
        "phone": "(11) 98888-7777",
        **overrides,
    }


def order_payload(items: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    return {
        "full_name": "Carlos Souza",
        "phone": "11977776666",
        "address": "Av. Brasil, 500 apto 12",
        "reference_point": "Ao lado da padaria",
        "payment_method": "pix",
        "items": items,
        **overrides,
    }


async def history_rows(factory: async_sessionmaker[AsyncSession], model: type) -> list[Any]:
    table = model.__history_table__
    async with factory() as session:
        result = await session.execute(select(table).order_by(table.c.valid_from))
        return list(result.mappings().all())


async def register(
    client: AsyncClient,
    identity: FakeIdentityProvider,
    uid: str,
    *,
    open_now: bool = True,
    **overrides: Any,
) -> tuple[str, dict[str, Any]]:
    token = identity.add_user(uid)
    response = await client.post(
        f"{API}/establishments", json=establishment_payload(**overrides), headers=auth(token)
    )
    assert response.status_code == 201, response.text
    if open_now:
        await set_hours(client, token, ALL_DAY)
    return token, response.json()


async def set_hours(client: AsyncClient, token: str, days: list[dict[str, Any]]) -> None:
    response = await client.put(f"{API}/opening-hours", json={"days": days}, headers=auth(token))
    assert response.status_code == 200, response.text


async def update_establishment(client: AsyncClient, token: str, **changes: Any) -> dict[str, Any]:
    response = await client.patch(f"{API}/establishments/me", json=changes, headers=auth(token))
    assert response.status_code == 200, response.text
    return response.json()


async def create_product(
    client: AsyncClient, token: str, name: str = "X-Burguer", price: float = 30, **extra: Any
) -> dict[str, Any]:
    response = await client.post(
        f"{API}/products", json={"name": name, "price": price, **extra}, headers=auth(token)
    )
    assert response.status_code == 201, response.text
    return response.json()


async def place(
    client: AsyncClient,
    slug: str,
    items: list[dict[str, Any]],
    device: str | None = None,
    headers: dict[str, str] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    response = await client.post(
        f"{API}/establishments/{slug}/orders",
        json=order_payload(items, **overrides),
        headers={**customer(device), **(headers or {})},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def register_push(
    client: AsyncClient, role: str, fcm_token: str, headers: dict[str, str]
) -> None:
    response = await client.post(
        f"{API}/push-devices", json={"fcm_token": fcm_token, "role": role}, headers=headers
    )
    assert response.status_code == 204, response.text
