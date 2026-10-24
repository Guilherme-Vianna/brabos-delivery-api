from app.models.customer import Customer
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    model = Customer

    async def get_by_firebase_uid(self, firebase_uid: str) -> Customer | None:
        return await self.get_by(firebase_uid=firebase_uid)
