
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment


class PaymentRepository:
    """Запросы к БД для работы с платежами."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payment: Payment) -> None:
        """Добавляет платеж в сессию."""
        self._session.add(payment)
