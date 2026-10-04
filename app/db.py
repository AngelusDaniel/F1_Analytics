import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://f1:f1@localhost:5432/f1"
)


def normalize_url(url: str) -> str:
    """Neon e Render entregam 'postgres://' ou 'postgresql://'.
    O SQLAlchemy com psycopg 3 precisa de 'postgresql+psycopg://'."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


# pool_pre_ping: testa a conexão antes de usar (o banco gratuito suspende quando ocioso)
engine = create_engine(normalize_url(DATABASE_URL), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """Dependência do FastAPI: abre uma sessão por requisição e fecha no fim."""
    with SessionLocal() as session:
        yield session
