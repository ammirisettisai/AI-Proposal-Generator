
import os
import ssl

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if database_url:
    # Neon PostgreSQL cloud database
    url = make_url(database_url).set(
        drivername="postgresql+pg8000",
        query={}
    )

    engine = create_engine(
        url,
        connect_args={
            "ssl_context": ssl.create_default_context()
        },
        poolclass=NullPool,
        pool_pre_ping=True
    )

else:
    # Local PostgreSQL fallback
    db_password = os.getenv("DB_PASSWORD")

    if not db_password:
        raise RuntimeError(
            "DATABASE_URL or DB_PASSWORD is missing"
        )

    local_url = URL.create(
        drivername="postgresql+pg8000",
        username=os.getenv("DB_USER", "postgres"),
        password=db_password,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "proposalai_db")
    )

    engine = create_engine(
        local_url,
        pool_pre_ping=True,
        poolclass=NullPool
    )

Base = declarative_base()


def test_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))
        return result.scalar()
