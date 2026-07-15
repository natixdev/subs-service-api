from enum import StrEnum


class Category(StrEnum):
    """Категория обязательства."""

    SUBSCRIPTION = 'subscription'
    WARRANTY = 'warranty'
    BILL = 'bill'
    INSURANCE = 'insurance'


class Recurrence(StrEnum):
    """Периодичность подписки."""

    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    YEARLY = 'yearly'


class Status(StrEnum):
    """Статус обязательства."""

    ACTIVE = 'active'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'
