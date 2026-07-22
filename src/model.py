from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from src.database import Base

class Slide(Base):
    __tablename__ = "slides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quickhash = Column(String, unique=True, nullable=False, index=True)   # hash değeri
    filename = Column(String, nullable=False)
    properties = Column(JSONB, nullable=True)  # Tüm ham metadatalar şimdilik bi dursun
    created_at = Column(DateTime(timezone=True), server_default=func.now()) #  oluşturulma tarihi