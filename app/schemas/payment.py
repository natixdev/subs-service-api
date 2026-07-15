from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

CurrencyField = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=3,
        pattern=r'^[A-Z]{3}$',
    ),
]


class PaymentOut(BaseModel):
    """Схема платежа."""

    id: UUID
    obligation_id: UUID
    amount: Decimal
    currency: CurrencyField
    paid_at: datetime

    model_config = ConfigDict(from_attributes=True)
