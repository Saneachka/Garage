from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from sqlalchemy import delete, select

from backend.api import (
    appointments, attachments, auth, diagnostics, schedule, services, users,
    vehicles, work_orders,
)
from backend.core.database import SessionLocal
from backend.core.models import Role, UserSession

ROLES = [
    ("client", "Клиент"),
    ("admin", "Администратор"),
    ("master", "Мастер-диагност"),
]


def seed_roles():
    db = SessionLocal()
    try:
        for code, name in ROLES:
            if not db.scalar(select(Role).where(Role.code == code)):
                db.add(Role(code=code, name=name))
        
        db.execute(delete(UserSession).where(UserSession.expires_at < datetime.utcnow()))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_roles()
    yield


app = FastAPI(title="Garage", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(services.router)
app.include_router(vehicles.router)
app.include_router(schedule.masters_router)
app.include_router(schedule.slots_router)
app.include_router(appointments.router)
app.include_router(diagnostics.router)
app.include_router(work_orders.router)
app.include_router(users.profile_router)
app.include_router(users.users_router)
app.include_router(users.groups_router)
app.include_router(attachments.router)

@app.get("/")
def root():
    return {"message": "Garage работает"}