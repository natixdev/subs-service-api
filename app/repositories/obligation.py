from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.obligation import Obligation


class ObligationRepository:
    """Запросы к БД для работы с обязательствами."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, obligation: Obligation) -> Obligation:
        """Создает обязательство."""
        self._session.add(obligation)
        await self._session.flush()
        await self._session.refresh(obligation)
        return obligation

    async def get_by_id(self, obligation_id: UUID) -> Obligation | None:
        """Возвращает обязательство по id или None, если не найдено."""
        statement = select(Obligation).where(Obligation.id == obligation_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def delete(self, obligation: Obligation) -> None:
        """Удаляет обязательство."""
        await self._session.delete(obligation)

    async def commit(self) -> None:
        """Фиксирует изменения."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Откатывает изменения."""
        await self._session.rollback()
