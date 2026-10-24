from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Establishment
from app.models.base import utc_now
from tests.fakes import FakeIdentityProvider, FakeIntegrations, FakePaymentGateway
from tests.helpers import (
    API,
    VALID_CNPJ,
    auth,
    create_product,
    establishment_payload,
    history_rows,
    place,
    register,
    set_hours,
    update_establishment,
)


async def test_register_generates_slug_and_red_defaults(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    _, body = await register(client, identity, "owner-1", name="Brabos Burguér!")

    assert body["slug"] == "brabos-burguer"
    assert (body["primary_color"], body["accent_color"]) == ("#D62828", "#FFB703")
    assert body["phone"] == "11988887777"
    assert (body["auto_accept"], body["delivery_fee_enabled"]) == (False, False)


async def test_duplicate_names_get_unique_slugs(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    _, first = await register(client, identity, "owner-1")
    _, second = await register(client, identity, "owner-2")

    assert (first["slug"], second["slug"]) == ("brabos-burguer", "brabos-burguer-2")


async def test_one_establishment_per_user(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, _ = await register(client, identity, "owner-1")
    response = await client.post(
        f"{API}/establishments", json=establishment_payload(), headers=auth(token)
    )

    assert response.status_code == 409


async def test_cnpj_and_slug_are_validated(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token = identity.add_user("owner-1")
    for payload in (
        {"cnpj": "11222333000180"},
        {"cnpj": "11111111111111"},
        {"slug": "me"},
        {"slug": "Not Valid!"},
    ):
        response = await client.post(
            f"{API}/establishments", json=establishment_payload(**payload), headers=auth(token)
        )
        assert response.status_code == 422, payload

    response = await client.post(
        f"{API}/establishments",
        json=establishment_payload(cnpj="11.222.333/0001-81", slug="Brabos"),
        headers=auth(token),
    )
    assert response.status_code == 201
    assert (response.json()["cnpj"], response.json()["slug"]) == (VALID_CNPJ, "brabos")


async def test_update_profile_colors_and_fee(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, _ = await register(client, identity, "owner-1")

    body = await update_establishment(
        client,
        token,
        primary_color="#1a2b3c",
        delivery_fee_enabled=True,
        delivery_fee=7.5,
        auto_accept=True,
    )
    invalid = await client.patch(
        f"{API}/establishments/me", json={"primary_color": "red"}, headers=auth(token)
    )
    null_name = await client.patch(
        f"{API}/establishments/me", json={"name": None}, headers=auth(token)
    )

    assert (body["primary_color"], body["delivery_fee"], body["auto_accept"]) == (
        "#1A2B3C",
        7.5,
        True,
    )
    assert invalid.status_code == null_name.status_code == 422


async def test_slug_change_conflicts(client: AsyncClient, identity: FakeIdentityProvider) -> None:
    token, _ = await register(client, identity, "owner-1")
    await register(client, identity, "owner-2", slug="taken")

    response = await client.patch(
        f"{API}/establishments/me", json={"slug": "taken"}, headers=auth(token)
    )

    assert response.status_code == 409


async def test_public_profile_reports_open_status(
    client: AsyncClient, identity: FakeIdentityProvider
) -> None:
    token, body = await register(client, identity, "owner-1", open_now=False)
    url = f"{API}/establishments/{body['slug']}"

    closed = (await client.get(url)).json()
    await set_hours(
        client, token, [{"weekday": d, "opens_at": "06:00", "closes_at": "05:59"} for d in range(7)]
    )
    opened = (await client.get(url)).json()
    absence = await client.post(
        f"{API}/absences",
        json={
            "starts_at": (utc_now() - timedelta(minutes=5)).isoformat(),
            "ends_at": (utc_now() + timedelta(hours=1)).isoformat(),
            "reason": "Falta de gás",
        },
        headers=auth(token),
    )
    absent = (await client.get(url)).json()

    assert closed["is_open"] is False
    assert opened["is_open"] is True
    assert absence.status_code == 201
    assert (absent["is_open"], absent["absence_reason"]) == (False, "Falta de gás")
    assert "firebase_uid" not in opened and "auto_accept" not in opened


async def test_unknown_slug_is_404(client: AsyncClient) -> None:
    assert (await client.get(f"{API}/establishments/nope")).status_code == 404


async def test_online_payments_require_gateway(
    client: AsyncClient, identity: FakeIdentityProvider, integrations: FakeIntegrations
) -> None:
    token, _ = await register(client, identity, "owner-1")

    rejected = await client.patch(
        f"{API}/establishments/me", json={"online_payments_enabled": True}, headers=auth(token)
    )
    integrations.gateway = FakePaymentGateway()
    accepted = await update_establishment(client, token, online_payments_enabled=True)

    assert rejected.status_code == 422
    assert accepted["online_payments_enabled"] is True


async def test_unregister_purges_everything(
    client: AsyncClient,
    identity: FakeIdentityProvider,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    token, body = await register(client, identity, "owner-1")
    product = await create_product(client, token)
    await place(client, body["slug"], [{"product_id": product["id"]}])
    await client.post(f"{API}/courier-invites", headers=auth(token))

    response = await client.delete(f"{API}/establishments/me", headers=auth(token))
    again = await client.get(f"{API}/establishments/me", headers=auth(token))

    assert response.status_code == 204
    assert again.status_code == 404
    rows = await history_rows(session_factory, Establishment)
    assert [row["operation"] for row in rows] == ["insert", "update", "delete"]
    assert rows[0]["changed_by"] == "owner-1"
