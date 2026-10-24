from httpx import AsyncClient

from tests.fakes import FakeIdentityProvider
from tests.helpers import API, auth


async def test_customer_profile_upsert(client: AsyncClient, identity: FakeIdentityProvider) -> None:
    token = identity.add_user("customer-1")
    payload = {"full_name": "Ana Lima", "phone": "11912345678", "address": "Rua A, 10"}

    missing = await client.get(f"{API}/customers/me", headers=auth(token))
    created = await client.put(f"{API}/customers/me", json=payload, headers=auth(token))
    updated = await client.put(
        f"{API}/customers/me",
        json={**payload, "reference_point": "Portão azul"},
        headers=auth(token),
    )
    loaded = await client.get(f"{API}/customers/me", headers=auth(token))

    assert missing.status_code == 404
    assert created.json()["id"] == updated.json()["id"]
    assert loaded.json()["reference_point"] == "Portão azul"
