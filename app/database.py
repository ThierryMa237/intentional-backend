from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = (
    os.getenv("DATABASE_URL") or
    os.getenv("DATABASE_PUBLIC_URL") or
    os.getenv("POSTGRES_URL")
)

if not DATABASE_URL:
    raise RuntimeError(
        "Aucune URL de base de données trouvée. "
        "Définis DATABASE_URL (ou DATABASE_PUBLIC_URL / POSTGRES_URL)."
    )

# Certains hébergeurs fournissent encore le schéma "postgres://",
# que SQLAlchemy 2 refuse.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
