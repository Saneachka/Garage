from fastapi import APIRouter
from app.core.config import settings
from app.api.v1 import auth, vehicles, service_types, orders, appointments, invoices, parts


api_router = APIRouter(prefix=settings.API_V1_STR)

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["Vehicles"])
api_router.include_router(service_types.router, prefix="/service-types", tags=["Service Types"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["Invoices"])
api_router.include_router(parts.router, prefix="/parts", tags=["Parts"])