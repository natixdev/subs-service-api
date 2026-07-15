from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.enums import Category, Status
from app.repositories.obligation import ObligationRepository
from app.repositories.payment import PaymentRepository
from app.schemas.obligation import (
    ObligationCreate,
    ObligationCreateResponse,
    ObligationOut,
    PayResponse,
    UpcomingResponse,
)
from app.services.obligation import ObligationService

router = APIRouter(prefix='/obligations', tags=['Obligations'])

DbSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


def _build_service(session: AsyncSession) -> ObligationService:
    """Создает сервис обязательств."""
    return ObligationService(
        session=session,
        obligation_repository=ObligationRepository(session),
        payment_repository=PaymentRepository(session),
    )


@router.post(
    '',
    response_model=ObligationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_obligation(
    data: ObligationCreate,
    session: DbSession,
) -> ObligationCreateResponse:
    """Создает новое обязательство."""
    service = _build_service(session)
    return await service.create(data)


@router.get(
    '',
    response_model=list[ObligationOut],
)
async def list_obligations(
    session: DbSession,
    category: Category | None = Query(default=None),
    status_filter: Status | None = Query(
        default=None,
        alias='status',
    ),
) -> list[ObligationOut]:
    """Возвращает список обязательств."""
    service = _build_service(session)
    return await service.list_with_lazy_expiry(
        category=category,
        status=status_filter,
    )


@router.get(
    '/upcoming',
    response_model=UpcomingResponse,
)
async def upcoming_obligations(
    session: DbSession,
    days: int = Query(default=7, ge=1),
) -> UpcomingResponse:
    """Возвращает ближайшие обязательства."""
    service = _build_service(session)
    return await service.upcoming(days)


@router.post(
    '/{obligation_id}/pay',
    response_model=PayResponse,
)
async def pay_obligation(
    obligation_id: UUID,
    session: DbSession,
) -> PayResponse:
    """Фиксирует оплату обязательства."""
    service = _build_service(session)
    return await service.pay(obligation_id)


@router.patch(
    '/{obligation_id}/cancel',
    response_model=ObligationOut,
)
async def cancel_obligation(
    obligation_id: UUID,
    session: DbSession,
) -> ObligationOut:
    """Отменяет обязательство."""
    service = _build_service(session)
    return await service.cancel(obligation_id)


@router.delete(
    '/{obligation_id}',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_obligation(
    obligation_id: UUID,
    session: DbSession,
) -> None:
    """Удаляет обязательство."""
    service = _build_service(session)
    await service.delete(obligation_id)
