"""
SQLite veritabanı bağlantı yapılandırması.

NullPool kullanılır: SQLite dosya tabanlıdır, bağlantı açmak ucuzdur.
QueuePool (varsayılan) WebSocket akışları + thread havuzu kombinasyonunda
"pool overflow" hatasına yol açar; NullPool bunu ortadan kaldırır.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
os.makedirs(DB_DIR, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'nvr_system.db')}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,  # her Session bağımsız bağlantı — pool tükenmesi yok
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — request başına bir DB session açar, biter bitmez kapatır."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
