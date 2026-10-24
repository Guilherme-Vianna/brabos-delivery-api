from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PushMessage:
    title: str
    body: str
    data: dict[str, str] = field(default_factory=dict)


class PushNotifier(Protocol):
    async def send(self, tokens: Sequence[str], message: PushMessage) -> list[str]: ...
