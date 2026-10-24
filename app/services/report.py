from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.models.base import utc_now
from app.models.order import Order, OrderStatus, PaymentStatus
from app.repositories.establishment import EstablishmentRepository
from app.repositories.order import OrderRepository
from app.schemas.report import DailySales, PaymentBreakdown, ProductSales, SalesReport
from app.services.common import local_zone, require_establishment

DEFAULT_PERIOD = timedelta(days=30)
TOP_PRODUCTS = 20
HALF = Decimal("0.5")


def counts_as_sale(order: Order) -> bool:
    return order.status is not OrderStatus.CANCELLED and order.payment_status not in (
        PaymentStatus.PENDING,
        PaymentStatus.REFUNDED,
    )


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.establishments = EstablishmentRepository(session)
        self.orders = OrderRepository(session)

    async def sales(
        self,
        user: AuthenticatedUser,
        starts_from: datetime | None,
        starts_until: datetime | None,
    ) -> SalesReport:
        establishment = await require_establishment(self.establishments, user)
        until = starts_until or utc_now()
        since = starts_from or until - DEFAULT_PERIOD
        orders = await self.orders.in_period(establishment.id, since, until)
        sales = [order for order in orders if counts_as_sale(order)]
        cancelled = [order for order in orders if order.status is OrderStatus.CANCELLED]
        revenue = sum((order.total for order in sales), Decimal(0))

        by_method: dict = defaultdict(lambda: [0, Decimal(0)])
        by_day: dict = defaultdict(lambda: [0, Decimal(0)])
        products: dict[UUID, list] = {}
        for order in sales:
            by_method[order.payment_method][0] += 1
            by_method[order.payment_method][1] += order.total
            day = order.created_at.astimezone(local_zone()).date()
            by_day[day][0] += 1
            by_day[day][1] += order.total
            for item in order.items:
                halves = [(item.product_id, item.product_name)]
                if item.half_product_id and item.half_product_name:
                    halves.append((item.half_product_id, item.half_product_name))
                share = Decimal(1) / len(halves)
                for product_id, name in halves:
                    entry = products.setdefault(product_id, [name, Decimal(0), Decimal(0)])
                    entry[1] += share * item.quantity
                    entry[2] += item.line_total * share

        ranking = sorted(products.items(), key=lambda pair: (-pair[1][1], -pair[1][2]))
        return SalesReport(
            starts_from=since,
            starts_until=until,
            orders=len(sales),
            revenue=revenue,
            average_ticket=(revenue / len(sales)).quantize(Decimal("0.01"))
            if sales
            else Decimal(0),
            delivery_fees=sum((order.delivery_fee for order in sales), Decimal(0)),
            cancelled_orders=len(cancelled),
            cancelled_value=sum((order.total for order in cancelled), Decimal(0)),
            by_payment_method=[
                PaymentBreakdown(method=method, orders=count, revenue=total)
                for method, (count, total) in sorted(by_method.items(), key=lambda p: -p[1][1])
            ],
            by_day=[
                DailySales(day=day, orders=count, revenue=total)
                for day, (count, total) in sorted(by_day.items())
            ],
            top_products=[
                ProductSales(
                    product_id=product_id,
                    name=name,
                    quantity=float(quantity),
                    revenue=total.quantize(Decimal("0.01")),
                )
                for product_id, (name, quantity, total) in ranking[:TOP_PRODUCTS]
            ],
        )
