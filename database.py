import os
import logging
import urllib.parse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

logger = logging.getLogger(__name__)

# 支持通过分离的环境变量连接（这样密码里带 @ 等特殊符号就不会出错）
db_host = os.getenv("DB_HOST", "db")
db_port = os.getenv("DB_PORT", "3306")
db_user = os.getenv("DB_USER", "invoice_user")
db_password = os.getenv("DB_PASSWORD", "invoice_password")
db_name = os.getenv("DB_NAME", "invoice_db")

# 对密码进行 URL 编码转义，防止密码中的 @ / # 等特殊字符破坏正确的连接字符串解析
encoded_password = urllib.parse.quote_plus(db_password)

# 如果显示指定了 DATABASE_URL 则优先用它，否则使用拼接转义后的字符串
default_url = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
DATABASE_URL = os.getenv("DATABASE_URL", default_url)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

class InvoiceRecord(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, default=0)
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
