from datetime import UTC, datetime, timedelta

import pytest

from app.core.storage import VIEW_URL_WINDOW_SECONDS, view_expires_at
from app.integrations import storage_views
from app.integrations.storage_views import ViewUrlCache


def test_view_expiry_is_stable_within_a_window_and_lasts_at_least_one() -> None:
    start = datetime(2026, 10, 25, 12, 0, 0, tzinfo=UTC)
    window = timedelta(seconds=VIEW_URL_WINDOW_SECONDS)

    assert view_expires_at(start) == view_expires_at(start + window - timedelta(seconds=1))
    assert view_expires_at(start + window) == view_expires_at(start) + window
    assert view_expires_at(start + window - timedelta(seconds=1)) - start >= window


async def test_view_urls_are_signed_once_per_window(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, datetime]] = []

    def sign(key: str, expires_at: datetime) -> str:
        calls.append((key, expires_at))
        return f"signed/{key}/{len(calls)}"

    cache = ViewUrlCache(sign)
    first = await cache.get("a.webp")
    again = await cache.get("a.webp")
    other = await cache.get("b.webp")

    assert first == again == "signed/a.webp/1"
    assert other == "signed/b.webp/2"

    monkeypatch.setattr(storage_views, "utc_now", lambda: datetime.now(UTC) + timedelta(hours=2))
    assert await cache.get("a.webp") == "signed/a.webp/3"


async def test_view_url_cache_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(storage_views, "MAX_CACHED_URLS", 2)
    cache = ViewUrlCache(lambda key, expires_at: key)

    for key in ("a", "b", "c"):
        await cache.get(key)

    assert [key for key, _ in cache._urls] == ["b", "c"]
