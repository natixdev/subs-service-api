from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.obligation import Obligation


class Payment(Base):
    """Модель истории оплат."""

    __tablename__ = 'payments'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    obligation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('obligations.id', ondelete='CASCADE'), nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    obligation: Mapped['Obligation'] = relationship(back_populates='payments')

    def __str__(self) -> str:
        return (
            f'{self.__class__.__name__} ({self.obligation}) '
            f'{self.paid_at} - {self.amount}'
        )
