import asyncio
import logging
from collections.abc import Sequence
from functools import lru_cache

from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError

from app.core.config import settings
from app.core.push import PushMessage
from app.integrations.firebase import get_identity_provider

logger = logging.getLogger(__name__)
INVALID_TOKEN_ERRORS = (messaging.UnregisteredError, messaging.SenderIdMismatchError)


class FirebasePushNotifier:
    def __init__(self) -> None:
        self._app = get_identity_provider().app

    async def send(self, tokens: Sequence[str], message: PushMessage) -> list[str]:
        if not tokens:
            return []
        multicast = messaging.MulticastMessage(
            tokens=list(tokens),
            data={"title": message.title, "body": message.body, **message.data},
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=message.title, body=message.body, tag=message.data.get("tag")
                ),
                fcm_options=messaging.WebpushFCMOptions(link=message.data.get("url")),
            ),
        )
        try:
            response = await asyncio.to_thread(
                messaging.send_each_for_multicast, multicast, False, self._app
            )
        except FirebaseError, ValueError:
            logger.exception("Push delivery failed")
            return []
        return [
            token
            for token, result in zip(tokens, response.responses, strict=True)
            if result.exception is not None and isinstance(result.exception, INVALID_TOKEN_ERRORS)
        ]


@lru_cache
def get_push_notifier() -> FirebasePushNotifier | None:
    return FirebasePushNotifier() if settings.push_enabled else None
