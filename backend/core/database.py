import os

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL") or URL.create(
    "postgresql+psycopg",
    username=os.environ.get("POSTGRES_USER", "garage"),
    password=os.environ["POSTGRES_PASSWORD"],
    host=os.environ.get("POSTGRES_HOST", "localhost"),
    port=int(os.environ.get("POSTGRES_PORT", "5432")),
    database=os.environ.get("POSTGRES_DB", "garage"),
).render_as_string(hide_password=False)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as db:
        yield db
