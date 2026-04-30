from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, index=True)
    status = Column(String, default="queued") # queued, processing, completed, failed
    progress = Column(Float, default=0.0)
    client_id = Column(String, index=True, nullable=True)
    file_hash = Column(String, index=True, nullable=True)
    ip_address = Column(String, index=True, nullable=True)
    original_file_name = Column(String)
    output_format = Column(String, default="mp3")
    split_mode = Column(String, default="ai_split")
    quality_preset = Column(String, default="high")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class DailyUsage(Base):
    __tablename__ = "daily_usage"
    id = Column(String, primary_key=True, index=True)
    client_id = Column(String, index=True, nullable=True)
    ip_address = Column(String, index=True, nullable=False)
    usage_date = Column(String, index=True, nullable=False)
    rewarded_credits = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class PremiumEntitlement(Base):
    __tablename__ = "premium_entitlements"
    client_id = Column(String, primary_key=True, index=True)
    purchase_token = Column(String, nullable=True)
    product_id = Column(String, nullable=True)
    activated_at = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
