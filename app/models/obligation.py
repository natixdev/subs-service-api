import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum as SAEnum, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import Category, Recurrence, Status

if TYPE_CHECKING:
    from app.models.payment import Payment


def _enum_values(enum_cls: type[Category] | type[Recurrence] | type[Status]) -> list[str]:
    """Возвращает  значения enum для хранения в БД."""
    return [member.value for member in enum_cls]


class Obligation(Base):
    """Модель обязательств (подписка, счёт на оплату и т.п.)."""

    __tablename__ = 'obligations'
    __table_args__ = (
        Index('ix_obligations_next_payment_date', 'next_payment_date'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    category: Mapped[Category] = mapped_column(
        SAEnum(Category, name='category', values_callable=_enum_values),
        nullable=False,
    )
    recurrence: Mapped[Recurrence | None] = mapped_column(
        SAEnum(Recurrence, name='recurrence', values_callable=_enum_values),
        nullable=True,
    )
    next_payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[Status] = mapped_column(
        SAEnum(Status, name='status', values_callable=_enum_values),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    payments: Mapped[list['Payment']] = relationship(
        back_populates='obligation',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    def __str__(self):
        return (f'{self.__class__.__name__} ({self.category}) {self.title}')
