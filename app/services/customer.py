from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.core.exceptions import NotFoundError
from app.models.customer import Customer
from app.repositories.customer import CustomerRepository
from app.repositories.establishment import EstablishmentRepository
from app.repositories.order import OrderRepository
from app.schemas.customer import CustomerUpsert
from app.schemas.order import CustomerOrderRead, OrderRead


class CustomerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.customers = CustomerRepository(session)
        self.orders = OrderRepository(session)
        self.establishments = EstablishmentRepository(session)

    async def get(self, user: AuthenticatedUser) -> Customer:
        customer = await self.customers.get_by_firebase_uid(user.uid)
        if customer is None:
            raise NotFoundError("Customer profile not found")
        return customer

    async def upsert(self, user: AuthenticatedUser, data: CustomerUpsert) -> Customer:
        customer = await self.customers.get_by_firebase_uid(user.uid)
        if customer is None:
            customer = await self.customers.add(
                Customer(firebase_uid=user.uid, **data.model_dump())
            )
        else:
            for field, value in data.model_dump().items():
                setattr(customer, field, value)
            await self.customers.save(customer)
        await self.session.commit()
        return customer

    async def orders_of(
        self, user: AuthenticatedUser, *, offset: int, limit: int
    ) -> tuple[list[CustomerOrderRead], int]:
        orders, total = await self.orders.list_for_customer(
            offset=offset, limit=limit, customer_uid=user.uid
        )
        names = {}
        for establishment_id in {order.establishment_id for order in orders}:
            establishment = await self.establishments.get(establishment_id)
            if establishment is not None:
                names[establishment_id] = establishment
        items = [
            CustomerOrderRead(
                **OrderRead.model_validate(order).model_dump(),
                establishment_slug=names[order.establishment_id].slug,
                establishment_name=names[order.establishment_id].name,
            )
            for order in orders
            if order.establishment_id in names
        ]
        return items, total
