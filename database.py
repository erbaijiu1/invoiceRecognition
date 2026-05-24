import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://invoice_user:invoice_password@db:3306/invoice_db")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

class InvoiceRecord(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), index=True)
    invoice_number = Column(String(100), index=True)
    invoice_date = Column(String(50))
    invoice_type = Column(String(100))
    digital_invoice_number = Column(String(100), index=True)
    seller_name = Column(String(255))
    buyer_name = Column(String(255))
    buyer_tax_id = Column(String(100))
    amount = Column(Float)
    tax_amount = Column(Float)
    valid_tax_amount = Column(Float)
    total_amount = Column(Float)
    recognition_time = Column(DateTime, default=datetime.utcnow)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
