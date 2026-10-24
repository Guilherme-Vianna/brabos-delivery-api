from fastapi import APIRouter

from app.api.v1.endpoints import (
    couriers,
    customers,
    establishments,
    orders,
    platform,
    products,
    schedule,
)

api_router = APIRouter()
api_router.include_router(establishments.router)
api_router.include_router(products.router)
api_router.include_router(schedule.router)
api_router.include_router(orders.router)
api_router.include_router(couriers.router)
api_router.include_router(customers.router)
api_router.include_router(platform.router)
