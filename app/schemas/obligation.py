from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.core.enums import Category, Recurrence, Status
from app.schemas.payment import PaymentOut

CurrensyField = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=3,
        pattern=r'^[A-Z]{3}$',
    ),
]


class ObligationBase(BaseModel):
    """Базовые поля обязательства."""

    title: str = Field(max_length=255)
    amount: Decimal = Field(gt=0)
    currency: CurrensyField
    category: Category
    recurrence: Recurrence | None = None
    next_payment_date: date

    @field_validator('title')
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError('Название не может быть пустым')

        return value


class ObligationCreate(ObligationBase):
    """Схема создания обязательства."""


class ObligationOut(ObligationBase):
    """Схема обязательства в ответах API."""

    id: UUID
    status: Status
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ObligationCreateResponse(BaseModel):
    """Ответ при создании обязательства."""

    obligation: ObligationOut
    warning: str | None = None


class RenewalAlert(BaseModel):
    """Информация о ближайшем списании."""

    id: UUID
    title: str
    next_payment_date: date
    amount: Decimal
    currency: CurrensyField


class UpcomingResponse(BaseModel):
    """Ответ эндпоинта о ближайших обязательствах."""

    obligations: list[ObligationOut]
    totals: dict[str, Decimal]
    renewal_alerts: list[RenewalAlert]


class PayResponse(BaseModel):
    """Ответ после оплаты обязательства."""

    obligation: ObligationOut
    payment: PaymentOut
