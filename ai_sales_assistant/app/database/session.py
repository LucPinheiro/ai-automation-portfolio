import os
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def build_engine(database_url: str) -> Engine:
    # 🛠️ PARCHE CLAVE: Convierte postgres:// a postgresql:// para Vercel/Supabase
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # SQLite connections are shared across FastAPI's threadpool workers.
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)

# 🚀 CORRECCIÓN DEFINITIVA: Intenta leer DATABASE_URL o POSTGRES_URL directamente del sistema
raw_db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or get_settings().database_url

engine = build_engine(raw_db_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def is_database_available(session: Session) -> bool:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True
