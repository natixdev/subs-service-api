from datetime import date
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import Category, Status
from app.models.obligation import Obligation


class ObligationRepository:
    """Запросы к БД для работы с обязательствами."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, obligation: Obligation) -> None:
        """Добавляет обязательство в сессию."""
        self._session.add(obligation)

    async def get_by_id(self, obligation_id: UUID) -> Obligation | None:
        """Возвращает обязательство по идентификатору."""
        statement = select(Obligation).where(Obligation.id == obligation_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def find_active_by_title(self, title: str) -> Obligation | None:
        """Ищет активное обязательство с указанным названием."""
        statement = (
            select(Obligation)
            .where(
                func.lower(Obligation.title) == title.lower(),
                Obligation.status == Status.ACTIVE,
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def obligation_list(
        self, category: Category | None = None, status: Status | None = None,
    ) -> list[Obligation]:
        """Возвращает список обязательств."""
        statement = select(Obligation)

        if category is not None:
            statement = statement.where(Obligation.category == category)
        if status is not None:
            statement = statement.where(Obligation.status == status)

        statement = statement.order_by(Obligation.next_payment_date.asc())
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def lazy_expire(self) -> None:
        """Переводит просроченные разовые обязательства в expired."""
        statement = (
            update(Obligation)
            .where(
                Obligation.status == Status.ACTIVE,
                Obligation.recurrence.is_(None),
                Obligation.next_payment_date < date.today(),
            )
            .values(
                status=Status.EXPIRED,
                updated_at=func.now(),
            )
        )
        await self._session.execute(statement)

    async def upcoming(self, end_date: date) -> list[Obligation]:
        """Возвращает обязательства до указанной даты."""
        statement = (
            select(Obligation)
            .where(
                Obligation.next_payment_date >= date.today(),
                Obligation.next_payment_date <= end_date,
            )
            .order_by(Obligation.next_payment_date.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def delete(self, obligation: Obligation) -> None:
        """Удаляет обязательство."""
        await self._session.delete(obligation)
