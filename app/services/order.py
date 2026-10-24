import logging
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    UnprocessableError,
)
from app.core.payments import CheckoutLine, PaymentEvent, PaymentEventKind, PaymentGateway
from app.models.base import utc_now
from app.models.establishment import Establishment
from app.models.order import (
    Order,
    OrderActor,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.models.order_event import OrderEvent, OrderEventKind
from app.models.product import Product
from app.repositories.courier import CourierRepository
from app.repositories.establishment import EstablishmentRepository
from app.repositories.order import OrderItemRepository, OrderRepository
from app.repositories.order_event import OrderEventRepository
from app.repositories.product import ProductRepository
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.availability import Availability
from app.services.common import existing_establishment, hash_token, require_establishment
from app.services.notifications import Notifier

logger = logging.getLogger(__name__)

CANCELLABLE = {OrderStatus.PLACED, OrderStatus.ACCEPTED}
PAYMENT_EXPIRED_REASON = "Pagamento online não concluído"


def item_label(item: OrderItem) -> str:
    if item.half_product_name:
        return f"½ {item.product_name} + ½ {item.half_product_name}"
    return item.product_name


class OrderService:
    def __init__(
        self,
        session: AsyncSession,
        notifier: Notifier,
        gateway: PaymentGateway | None = None,
    ) -> None:
        self.session = session
        self.notifier = notifier
        self.gateway = gateway
        self.establishments = EstablishmentRepository(session)
        self.products = ProductRepository(session)
        self.orders = OrderRepository(session)
        self.items = OrderItemRepository(session)
        self.events = OrderEventRepository(session)
        self.couriers = CourierRepository(session)

    async def place(
        self,
        slug: str,
        data: OrderCreate,
        customer_token: str,
        user: AuthenticatedUser | None,
    ) -> tuple[Order, str | None]:
        establishment = await existing_establishment(self.establishments, slug)
        if not (await Availability(self.session).status(establishment)).is_open:
            raise ConflictError("Establishment is closed")
        online = data.payment_method is PaymentMethod.ONLINE
        if online and (self.gateway is None or not establishment.online_payments_enabled):
            raise UnprocessableError("Online payments are not available")
        items = await self._build_items(establishment, data.items)
        subtotal = sum((item.line_total for item in items), Decimal(0))
        if establishment.min_order is not None and subtotal < establishment.min_order:
            raise UnprocessableError("Order is below the minimum value")
        fee = establishment.delivery_fee if establishment.delivery_fee_enabled else Decimal(0)
        total = subtotal + fee
        if data.change_for is not None and data.change_for < total:
            raise UnprocessableError("change_for must cover the order total")

        locked = await self.establishments.lock(establishment.id)
        number = locked.next_order_number
        locked.next_order_number = number + 1
        await self.establishments.save(locked)
        auto_accept = locked.auto_accept and not online
        now = utc_now()
        order = await self.orders.add(
            Order(
                establishment_id=establishment.id,
                number=number,
                status=OrderStatus.ACCEPTED if auto_accept else OrderStatus.PLACED,
                accepted_at=now if auto_accept else None,
                payment_status=PaymentStatus.PENDING if online else PaymentStatus.NOT_REQUIRED,
                subtotal=subtotal,
                delivery_fee=fee,
                total=total,
                customer_token_hash=hash_token(customer_token),
                customer_uid=user.uid if user else None,
                **data.model_dump(exclude={"items"}),
            )
        )
        for item in items:
            item.order_id = order.id
            await self.items.add(item)
        actor_uid = user.uid if user else None
        await self.events.record(order, OrderEventKind.PLACED, OrderActor.CUSTOMER, actor_uid)
        if auto_accept:
            await self.events.record(
                order, OrderEventKind.ACCEPTED, OrderActor.SYSTEM, detail="auto_accept"
            )
        await self.session.commit()
        order = await self._load(order.id)

        if online:
            return order, await self._start_checkout(establishment, order)
        await self.notifier.order_placed(establishment, order)
        if auto_accept:
            await self.notifier.order_changed(establishment, order)
        return order, None

    async def list_mine(
        self,
        slug: str,
        customer_token: str,
        user: AuthenticatedUser | None,
        *,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Order], int]:
        establishment = await existing_establishment(self.establishments, slug)
        return await self.orders.list_for_customer(
            offset=offset,
            limit=limit,
            establishment_id=establishment.id,
            token_hash=hash_token(customer_token),
            customer_uid=user.uid if user else None,
        )

    async def get_mine(
        self, slug: str, order_id: UUID, customer_token: str, user: AuthenticatedUser | None
    ) -> Order:
        establishment = await existing_establishment(self.establishments, slug)
        return await self._mine(establishment, order_id, customer_token, user)

    async def cancel_mine(
        self,
        slug: str,
        order_id: UUID,
        customer_token: str,
        user: AuthenticatedUser | None,
        reason: str | None,
    ) -> Order:
        establishment = await existing_establishment(self.establishments, slug)
        order = await self._mine(establishment, order_id, customer_token, user)
        if order.status is not OrderStatus.PLACED:
            raise ConflictError("Order can no longer be cancelled")
        await self._cancel(order, OrderActor.CUSTOMER, user.uid if user else None, reason)
        await self.session.commit()
        await self.notifier.order_changed(establishment, order)
        return await self._load(order.id)

    async def list(
        self,
        user: AuthenticatedUser,
        *,
        offset: int,
        limit: int,
        statuses: Sequence[OrderStatus] | None,
        created_from: datetime | None,
        created_until: datetime | None,
    ) -> tuple[Sequence[Order], int]:
        establishment = await require_establishment(self.establishments, user)
        return await self.orders.list_for_establishment(
            establishment.id,
            offset=offset,
            limit=limit,
            statuses=statuses,
            created_from=created_from,
            created_until=created_until,
        )

    async def get(self, user: AuthenticatedUser, order_id: UUID) -> Order:
        establishment = await require_establishment(self.establishments, user)
        return await self._owned(establishment, order_id)

    async def accept(self, user: AuthenticatedUser, order_id: UUID) -> Order:
        establishment = await require_establishment(self.establishments, user)
        order = await self._owned(establishment, order_id)
        if order.status is not OrderStatus.PLACED:
            raise ConflictError("Only placed orders can be accepted")
        if order.payment_status is PaymentStatus.PENDING:
            raise ConflictError("Order is waiting for online payment")
        await self._accept(order, OrderActor.OWNER, user.uid)
        await self.session.commit()
        await self.notifier.order_changed(establishment, order)
        return await self._load(order.id)

    async def deliver(self, user: AuthenticatedUser, order_id: UUID) -> Order:
        establishment = await require_establishment(self.establishments, user)
        order = await self._owned(establishment, order_id)
        await self._deliver(order, OrderActor.OWNER, user.uid)
        await self.session.commit()
        await self.notifier.order_changed(establishment, order)
        return await self._load(order.id)

    async def cancel(self, user: AuthenticatedUser, order_id: UUID, reason: str) -> Order:
        establishment = await require_establishment(self.establishments, user)
        order = await self._owned(establishment, order_id)
        if order.status not in CANCELLABLE:
            raise ConflictError("Order can no longer be cancelled")
        await self._cancel(order, OrderActor.OWNER, user.uid, reason)
        await self.session.commit()
        await self.notifier.order_changed(establishment, order)
        return await self._load(order.id)

    async def list_events(
        self,
        user: AuthenticatedUser,
        *,
        offset: int,
        limit: int,
        order_id: UUID | None,
        created_from: datetime | None,
        created_until: datetime | None,
    ) -> tuple[Sequence[OrderEvent], int]:
        establishment = await require_establishment(self.establishments, user)
        return await self.events.list_for_establishment(
            establishment.id,
            offset=offset,
            limit=limit,
            order_id=order_id,
            created_from=created_from,
            created_until=created_until,
        )

    async def list_for_courier(
        self, user: AuthenticatedUser, *, offset: int, limit: int
    ) -> tuple[Sequence[Order], int]:
        memberships = await self.couriers.active_for_uid(user.uid)
        if not memberships:
            return [], 0
        return await self.orders.list_for_couriers(
            [courier.establishment_id for courier in memberships], offset=offset, limit=limit
        )

    async def deliver_as_courier(self, user: AuthenticatedUser, order_id: UUID) -> Order:
        memberships = {
            courier.establishment_id: courier
            for courier in await self.couriers.active_for_uid(user.uid)
        }
        order = await self.orders.get_aggregate(order_id)
        if order is None or order.establishment_id not in memberships:
            raise NotFoundError(f"Order {order_id} not found")
        order.courier_id = memberships[order.establishment_id].id
        await self._deliver(order, OrderActor.COURIER, user.uid)
        await self.session.commit()
        establishment = await self.establishments.get(order.establishment_id)
        assert establishment is not None
        await self.notifier.order_changed(establishment, order)
        return await self._load(order.id)

    async def handle_payment(self, event: PaymentEvent) -> None:
        order = await self._order_for_payment(event)
        if order is None or order.payment_status is not PaymentStatus.PENDING:
            return
        establishment = await self.establishments.get(order.establishment_id)
        assert establishment is not None
        if event.kind is PaymentEventKind.PAID:
            order.payment_status = PaymentStatus.PAID
            if event.payment_reference:
                order.payment_reference = event.payment_reference
            await self.orders.save(order)
            await self.events.record(order, OrderEventKind.PAID, OrderActor.SYSTEM)
            if order.status is OrderStatus.CANCELLED:
                await self._refund(order)
            elif establishment.auto_accept:
                await self._accept(order, OrderActor.SYSTEM, None, detail="auto_accept")
            await self.session.commit()
            if order.status is not OrderStatus.CANCELLED:
                await self.notifier.order_placed(establishment, order)
            if order.status is OrderStatus.ACCEPTED:
                await self.notifier.order_changed(establishment, order)
        elif event.kind is PaymentEventKind.EXPIRED and order.status is OrderStatus.PLACED:
            await self._cancel(order, OrderActor.SYSTEM, None, PAYMENT_EXPIRED_REASON)
            await self.session.commit()
            await self.notifier.order_changed(establishment, order)

    async def _order_for_payment(self, event: PaymentEvent) -> Order | None:
        if event.order_id is not None:
            return await self.orders.get_aggregate(event.order_id)
        if event.checkout_reference is not None:
            found = await self.orders.get_by_payment_reference(event.checkout_reference)
            return await self.orders.get_aggregate(found.id) if found else None
        return None

    async def _start_checkout(self, establishment: Establishment, order: Order) -> str:
        assert self.gateway is not None
        lines = [
            CheckoutLine(name=item_label(item), unit_amount=item.unit_price, quantity=item.quantity)
            for item in order.items
        ]
        if order.delivery_fee > 0:
            lines.append(
                CheckoutLine(name="Taxa de entrega", unit_amount=order.delivery_fee, quantity=1)
            )
        return_url = (
            f"{settings.public_app_url.rstrip('/')}/e/{establishment.slug}/pedido/{order.id}"
        )
        try:
            checkout = await self.gateway.create_checkout(
                order.id, lines, f"{return_url}?pagamento=ok", f"{return_url}?pagamento=cancelado"
            )
        except Exception as exc:
            logger.exception("Could not create checkout for order %s", order.id)
            await self._cancel(order, OrderActor.SYSTEM, None, PAYMENT_EXPIRED_REASON)
            await self.session.commit()
            raise ServiceUnavailableError("Payment provider is unavailable") from exc
        order.payment_reference = checkout.reference
        await self.orders.save(order)
        await self.session.commit()
        return checkout.url

    async def _accept(
        self, order: Order, actor: OrderActor, actor_uid: str | None, detail: str | None = None
    ) -> None:
        order.status = OrderStatus.ACCEPTED
        order.accepted_at = utc_now()
        await self.orders.save(order)
        await self.events.record(order, OrderEventKind.ACCEPTED, actor, actor_uid, detail)

    async def _deliver(self, order: Order, actor: OrderActor, actor_uid: str) -> None:
        if order.status is not OrderStatus.ACCEPTED:
            raise ConflictError("Only accepted orders can be delivered")
        order.status = OrderStatus.DELIVERED
        order.delivered_at = utc_now()
        await self.orders.save(order)
        await self.events.record(order, OrderEventKind.DELIVERED, actor, actor_uid)

    async def _cancel(
        self, order: Order, actor: OrderActor, actor_uid: str | None, reason: str | None
    ) -> None:
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = utc_now()
        order.cancelled_by = actor
        order.cancel_reason = reason
        await self.orders.save(order)
        await self.events.record(order, OrderEventKind.CANCELLED, actor, actor_uid, reason)
        if order.payment_status is PaymentStatus.PAID:
            await self._refund(order)

    async def _refund(self, order: Order) -> None:
        if self.gateway is None or order.payment_reference is None:
            raise ServiceUnavailableError("Payment provider is unavailable for refunds")
        try:
            await self.gateway.refund(order.payment_reference)
        except Exception as exc:
            await self.session.rollback()
            raise ServiceUnavailableError("Refund failed; try again") from exc
        order.payment_status = PaymentStatus.REFUNDED
        await self.orders.save(order)
        await self.events.record(order, OrderEventKind.REFUNDED, OrderActor.SYSTEM)

    async def _build_items(
        self, establishment: Establishment, requested: Sequence[OrderItemCreate]
    ) -> list[OrderItem]:
        ids = {item.product_id for item in requested} | {
            item.half_product_id for item in requested if item.half_product_id
        }
        found = await self.products.find_for_establishment(establishment.id, ids)
        unavailable = sorted(
            str(product_id)
            for product_id in ids
            if product_id not in found or not found[product_id].active
        )
        if unavailable:
            raise UnprocessableError(f"Products are not available: {', '.join(unavailable)}")
        return [self._item(found, item) for item in requested]

    @staticmethod
    def _item(found: dict[UUID, Product], requested: OrderItemCreate) -> OrderItem:
        product = found[requested.product_id]
        half = found[requested.half_product_id] if requested.half_product_id else None
        if half is not None and not (product.allows_half and half.allows_half):
            raise UnprocessableError(f"{product.name} cannot be split in half")
        asks_doneness = product.asks_doneness or (half is not None and half.asks_doneness)
        if asks_doneness and requested.doneness is None:
            raise UnprocessableError(f"Choose the doneness for {product.name}")
        if not asks_doneness and requested.doneness is not None:
            raise UnprocessableError(f"{product.name} does not take a doneness")
        return OrderItem(
            product_id=product.id,
            half_product_id=half.id if half else None,
            product_name=product.name,
            half_product_name=half.name if half else None,
            unit_price=max(product.price, half.price) if half else product.price,
            quantity=requested.quantity,
            doneness=requested.doneness,
            notes=requested.notes or None,
        )

    async def _mine(
        self,
        establishment: Establishment,
        order_id: UUID,
        customer_token: str,
        user: AuthenticatedUser | None,
    ) -> Order:
        order = await self.orders.get_aggregate(order_id, establishment.id)
        owns = order is not None and (
            order.customer_token_hash == hash_token(customer_token)
            or (user is not None and order.customer_uid == user.uid)
        )
        if not owns:
            raise NotFoundError(f"Order {order_id} not found")
        assert order is not None
        return order

    async def _owned(self, establishment: Establishment, order_id: UUID) -> Order:
        order = await self.orders.get_aggregate(order_id, establishment.id)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found")
        return order

    async def _load(self, order_id: UUID) -> Order:
        order = await self.orders.get_aggregate(order_id)
        assert order is not None
        return order
