# database.py
from datetime import datetime, timezone
import os
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import DateTime, create_engine, Column, Integer, String, LargeBinary, Text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv(Path(__file__).parent / ".env") 

# --- Connection setup, built from .env values ---
CONN_STR = (
    f"DRIVER={os.getenv('DB_DRIVER')};"
    f"SERVER={os.getenv('DB_SERVER')};"
    f"DATABASE={os.getenv('DB_NAME')};"
    f"Trusted_Connection={os.getenv('DB_TRUSTED_CONNECTION')};"
)
params = urllib.parse.quote_plus(CONN_STR)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", echo=False)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Ticket(Base):
    __tablename__ = "Tickets"

    ticket_id = Column(String(50), primary_key=True)
    category = Column(String(100), nullable=False)
    subject = Column(String(500), nullable=False)
    description = Column(Text)
    resolution_notes = Column(Text)
    tags = Column(String(500))  # Stored as a comma-separated string
    created_at = Column(String(50))
    status = Column(String(50), nullable=False)
    Embedding = Column(LargeBinary)
    EmbeddingModelVersion = Column(String(50))


class TicketNew(Base):
    __tablename__ = "TicketsNew"

    ticket_id = Column(String(50), primary_key=True)
    subject = Column(String(500), nullable=False)
    description = Column(Text)
    Embedding = Column(LargeBinary)
    EmbeddingModelVersion = Column(String(50))

def init_db():
    Base.metadata.create_all(engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()