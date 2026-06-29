from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DocumentGeneration(Base):
    """Modelo que representa una generación de documento comercial."""

    __tablename__ = "document_generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    client_name: Mapped[str] = mapped_column(String(100), nullable=False)
    company: Mapped[str] = mapped_column(String(100), nullable=False)
    sector: Mapped[str] = mapped_column(String(80), nullable=False)
    product_service: Mapped[str] = mapped_column(String(150), nullable=False)
    customer_need: Mapped[str] = mapped_column(Text, nullable=False)

    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    tone: Mapped[str] = mapped_column(String(30), nullable=False)

    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)

    model_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    execution_time: Mapped[float | None] = mapped_column(Float, nullable=True)