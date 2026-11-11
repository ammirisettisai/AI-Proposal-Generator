
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# Load environment variables
load_dotenv()

# Read database settings
db_password = os.getenv("DB_PASSWORD")
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base

load_dotenv()

db_password = os.getenv("DB_PASSWORD")

if not db_password:
    raise RuntimeError("DB_PASSWORD is missing from the .env file")

database_url = URL.create(
    drivername="postgresql+pg8000",
    username=os.getenv("DB_USER", "postgres"),
    password=db_password,
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME", "proposalai_db")
)

engine = create_engine(
    database_url,
    pool_pre_ping=True
)

Base = declarative_base()


def test_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))
        return result.scalar()