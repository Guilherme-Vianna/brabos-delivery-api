import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.push import PushMessage, PushNotifier
from app.models.establishment import Establishment
from app.models.order import Order, OrderActor, OrderStatus
from app.models.push_device import PushRole
from app.repositories.courier import CourierRepository
from app.repositories.push_device import PushDeviceRepository

logger = logging.getLogger(__name__)

CUSTOMER_MESSAGES = {
    OrderStatus.ACCEPTED: ("Pedido aceito", "Seu pedido #{number} está sendo preparado."),
    OrderStatus.DELIVERED: ("Pedido entregue", "Seu pedido #{number} foi entregue. Bom apetite!"),
    OrderStatus.CANCELLED: ("Pedido cancelado", "Seu pedido #{number} foi cancelado."),
}


class Notifier:
    def __init__(self, session: AsyncSession, push: PushNotifier | None) -> None:
        self.session = session
        self.push = push
        self.devices = PushDeviceRepository(session)
        self.couriers = CourierRepository(session)

    async def order_placed(self, establishment: Establishment, order: Order) -> None:
        tokens = await self.devices.tokens_for(PushRole.OWNER, uids=[establishment.firebase_uid])
        message = PushMessage(
            title=f"Novo pedido #{order.number}",
            body=f"{order.full_name} · R$ {f'{order.total:.2f}'.replace('.', ',')}",
            data={"url": "/pedidos", "order_id": str(order.id), "kind": "placed", "tag": "orders"},
        )
        await self._send(tokens, message)

    async def order_changed(self, establishment: Establishment, order: Order) -> None:
        if order.cancelled_by is OrderActor.CUSTOMER:
            tokens = await self.devices.tokens_for(
                PushRole.OWNER, uids=[establishment.firebase_uid]
            )
            await self._send(
                tokens,
                PushMessage(
                    title=f"Pedido #{order.number} cancelado pelo cliente",
                    body=order.cancel_reason or order.full_name,
                    data={"url": "/pedidos", "order_id": str(order.id), "kind": "cancelled"},
                ),
            )
            return
        template = CUSTOMER_MESSAGES.get(order.status)
        if template is not None:
            tokens = await self.devices.tokens_for(
                PushRole.CUSTOMER, uids=[order.customer_uid], token_hash=order.customer_token_hash
            )
            title, body = template
            await self._send(
                tokens,
                PushMessage(
                    title=title,
                    body=body.format(number=order.number),
                    data={
                        "url": f"/e/{establishment.slug}/pedido/{order.id}",
                        "order_id": str(order.id),
                        "kind": order.status.value,
                        "tag": f"order-{order.id}",
                    },
                ),
            )
        if order.status is OrderStatus.ACCEPTED:
            uids = await self.couriers.active_uids(establishment.id)
            tokens = await self.devices.tokens_for(PushRole.COURIER, uids=uids)
            await self._send(
                tokens,
                PushMessage(
                    title=f"Entrega disponível · {establishment.name}",
                    body=f"Pedido #{order.number} · {order.address}",
                    data={"url": "/entregador", "order_id": str(order.id), "kind": "accepted"},
                ),
            )

    async def _send(self, tokens: list[str], message: PushMessage) -> None:
        if self.push is None or not tokens:
            return
        try:
            invalid = await self.push.send(tokens, message)
        except Exception:
            logger.exception("Push notification failed")
            return
        if invalid:
            for device in await self.devices.find_tokens(invalid):
                await self.devices.delete(device)
            await self.session.commit()
