from datetime import timedelta
from typing import Any

import pytest
from google.auth.credentials import Signing

from app.integrations import storage_gcs
from app.integrations.storage_gcs import GcsObjectStorage

SERVICE_ACCOUNT = "api@project.iam.gserviceaccount.com"


class TokenCredentials:
    def __init__(self) -> None:
        self.valid = False
        self.token: str | None = None
        self.service_account_email = "default"
        self.refreshes = 0

    def refresh(self, request: object) -> None:
        self.refreshes += 1
        self.valid = True
        self.token = "access-token"
        self.service_account_email = SERVICE_ACCOUNT


class KeyCredentials:
    valid = True


Signing.register(KeyCredentials)


class RecordingBlob:
    def __init__(self, calls: list[dict[str, Any]]) -> None:
        self.calls = calls

    def generate_signed_url(self, **kwargs: Any) -> str:
        self.calls.append(kwargs)
        return "https://signed.test/object"


class RecordingClient:
    calls: list[dict[str, Any]] = []

    def __init__(self, project: str | None, credentials: object) -> None: ...

    def bucket(self, name: str) -> RecordingClient:
        return self

    def blob(self, key: str) -> RecordingBlob:
        return RecordingBlob(self.calls)


def build(monkeypatch: pytest.MonkeyPatch, credentials: object) -> GcsObjectStorage:
    RecordingClient.calls = []
    monkeypatch.setattr(storage_gcs.google.auth, "default", lambda scopes: (credentials, "project"))
    monkeypatch.setattr(storage_gcs.storage, "Client", RecordingClient)
    return GcsObjectStorage("bucket")


async def test_token_only_credentials_sign_through_iam(monkeypatch: pytest.MonkeyPatch) -> None:
    credentials = TokenCredentials()
    gcs = build(monkeypatch, credentials)

    await gcs.presign_upload("a.webp", "image/webp")
    await gcs.presign_view("a.webp")
    await gcs.presign_view("b.webp")

    assert credentials.refreshes == 1
    assert len(RecordingClient.calls) == 3
    for call in RecordingClient.calls:
        assert call["service_account_email"] == SERVICE_ACCOUNT
        assert call["access_token"] == "access-token"
    assert RecordingClient.calls[0]["method"] == "PUT"
    assert RecordingClient.calls[0]["expiration"] == timedelta(seconds=600)
    assert RecordingClient.calls[1]["method"] == "GET"


async def test_key_credentials_sign_locally(monkeypatch: pytest.MonkeyPatch) -> None:
    gcs = build(monkeypatch, KeyCredentials())

    await gcs.presign_view("a.webp")

    assert "access_token" not in RecordingClient.calls[0]
    assert "service_account_email" not in RecordingClient.calls[0]
