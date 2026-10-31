from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

import auth
import vehicles
import services
from database import SessionLocal
from models import Role

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

@app.get("/")
def root():
    return {"message": "Garage работает"}