import asyncio
from collections import OrderedDict
from collections.abc import Callable
from datetime import datetime

from app.core.storage import view_expires_at
from app.models.base import utc_now

MAX_CACHED_URLS = 4096


class ViewUrlCache:
    def __init__(self, sign: Callable[[str, datetime], str]) -> None:
        self._sign = sign
        self._urls: OrderedDict[tuple[str, datetime], str] = OrderedDict()

    async def get(self, key: str) -> str:
        expires_at = view_expires_at(utc_now())
        entry = (key, expires_at)
        url = self._urls.get(entry)
        if url is None:
            url = await asyncio.to_thread(self._sign, key, expires_at)
            self._urls[entry] = url
            while len(self._urls) > MAX_CACHED_URLS:
                self._urls.popitem(last=False)
        return url
