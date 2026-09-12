from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.infrastructure.database import Base


class IncomeTaxBracket(Base):
    __tablename__ = "income_tax_brackets"
    __table_args__ = (
        UniqueConstraint(
            "source_document",
            "source_record_id",
            name="uq_income_tax_brackets_source_document_record_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    jurisdiction: Mapped[str] = mapped_column(String(120), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    income_min: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    income_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    source_document: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
