import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import Category, Recurrence, Status
from app.core.exceptions import (
    InvalidObligationStatusError,
    ObligationNotFoundError,
)
from app.core.sse import broadcast
from app.models.obligation import Obligation
from app.models.payment import Payment
from app.repositories.obligation import ObligationRepository
from app.repositories.payment import PaymentRepository
from app.schemas.obligation import (
    ObligationCreate,
    ObligationCreateResponse,
    ObligationOut,
    PayResponse,
    RenewalAlert,
    UpcomingResponse,
)
from app.schemas.payment import PaymentOut

logger = logging.getLogger(__name__)


class ObligationService:
    """Бизнес-логика работы с обязательствами."""

    def __init__(
        self,
        session: AsyncSession,
        obligation_repository: ObligationRepository,
        payment_repository: PaymentRepository,
    ) -> None:
        self._session = session
        self._obligation_repository = obligation_repository
        self._payment_repository = payment_repository

    async def create(
        self,
        data: ObligationCreate,
    ) -> ObligationCreateResponse:
        """Создает обязательство."""
        duplicate = await self._obligation_repository.find_active_by_title(
            data.title,
        )

        if data.recurrence is not None:
            obligation_status = Status.ACTIVE
        elif data.next_payment_date < date.today():
            obligation_status = Status.EXPIRED
        else:
            obligation_status = Status.ACTIVE

        obligation = Obligation(
            title=data.title,
            amount=data.amount,
            currency=data.currency,
            category=data.category,
            recurrence=data.recurrence,
            next_payment_date=data.next_payment_date,
            status=obligation_status,
        )

        await self._obligation_repository.create(obligation)
        await self._commit()
        await self._session.refresh(obligation)

        warning = None

        if duplicate is not None:
            warning = (
                'Активное обязательство '
                'с таким названием уже существует'
            )
        if warning is not None:
            logger.info('%s — %s', obligation.id, warning)

        return ObligationCreateResponse(
            obligation=ObligationOut.model_validate(obligation),
            warning=warning,
        )

    async def list_with_lazy_expiry(
        self,
        category: Category | None = None,
        status: Status | None = None,
    ) -> list[ObligationOut]:
        """Возвращает список обязательств с lazy expiry."""
        await self._obligation_repository.lazy_expire()
        await self._commit()

        obligations = await self._obligation_repository.obligation_list(
            category=category,
            status=status,
        )
        return [
            ObligationOut.model_validate(obligation)
            for obligation in obligations
        ]

    async def upcoming(
        self,
        days: int = 7,
    ) -> UpcomingResponse:
        """Возвращает ближайшие обязательства."""
        end_date = date.today() + relativedelta(days=days)
        obligations = await self._obligation_repository.upcoming(end_date)
        totals: dict[str, Decimal] = {}

        for obligation in obligations:
            totals.setdefault(
                obligation.currency,
                Decimal('0'),
            )
            totals[obligation.currency] += obligation.amount

        renewal_alerts = [
            RenewalAlert(
                id=obligation.id,
                title=obligation.title,
                next_payment_date=obligation.next_payment_date,
                amount=obligation.amount,
                currency=obligation.currency,
            )
            for obligation in obligations
            if (
                obligation.category == Category.SUBSCRIPTION
                and obligation.recurrence is not None
            )
        ]
        return UpcomingResponse(
            obligations=[
                ObligationOut.model_validate(obligation)
                for obligation in obligations
            ],
            totals=totals,
            renewal_alerts=renewal_alerts,
        )

    async def pay(
        self,
        obligation_id: UUID,
    ) -> PayResponse:
        """Фиксирует оплату обязательства."""
        obligation = await self._get_obligation(obligation_id)

        if obligation.status != Status.ACTIVE:
            raise InvalidObligationStatusError(obligation.status)

        payment = Payment(
            obligation_id=obligation.id,
            amount=obligation.amount,
            currency=obligation.currency,
        )
        await self._payment_repository.create(payment)

        if obligation.recurrence == Recurrence.MONTHLY:
            obligation.next_payment_date += relativedelta(months=1)
        elif obligation.recurrence == Recurrence.QUARTERLY:
            obligation.next_payment_date += relativedelta(months=3)
        elif obligation.recurrence == Recurrence.YEARLY:
            obligation.next_payment_date += relativedelta(years=1)
        elif obligation.recurrence is None:
            obligation.status = Status.CANCELLED

        await self._commit()
        await self._session.refresh(obligation)
        await self._session.refresh(payment)

        logger.info(
            'paid %s — %s %s', obligation.id, payment.amount, payment.currency,
        )
        return PayResponse(
            obligation=ObligationOut.model_validate(obligation),
            payment=PaymentOut.model_validate(payment),
        )

    async def cancel(
        self,
        obligation_id: UUID,
    ) -> ObligationOut:
        """Отменяет обязательство."""
        obligation = await self._get_obligation(obligation_id)

        if obligation.status != Status.ACTIVE:
            raise InvalidObligationStatusError(obligation.status)

        obligation.status = Status.CANCELLED

        await self._commit()
        await self._session.refresh(obligation)

        logger.info('cancelled %s', obligation.id)

        return ObligationOut.model_validate(obligation)

    async def delete(
        self,
        obligation_id: UUID,
    ) -> None:
        """Удаляет обязательство."""
        obligation = await self._get_obligation(obligation_id)

        await self._obligation_repository.delete(obligation)
        await self._commit()

        logger.info('deleted %s', obligation.id)

        try:
            await broadcast(
                'obligation_deleted',
                {
                    'type': 'obligation_deleted',
                    'id': str(obligation.id),
                },
            )
        except Exception:
            logger.exception('Ошибка отправки SSE после удаления')

    async def _commit(self) -> None:
        """Фиксирует транзакцию или откатывает ее при ошибке."""
        try:
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    async def _get_obligation(
        self,
        obligation_id: UUID,
    ) -> Obligation:
        """Возвращает обязательство или выбрасывает исключение."""
        obligation = await self._obligation_repository.get_by_id(
            obligation_id,
        )
        if obligation is None:
            raise ObligationNotFoundError(obligation_id)
        return obligation
