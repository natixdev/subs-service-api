import logging

from fastapi import FastAPI

from app.api.v1.obligations import router as obligations_router
from app.core.exceptions import (
    InvalidObligationStatusError,
    ObligationNotFoundError,
)
from app.core.exceptions_handler import (
    invalid_obligation_status_handler,
    obligation_not_found_handler,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title='s21_API для управления личными подписками и регулярными платежами',
    description='Тестовое задание, Хуснутдинова Н.А.',
)

app.add_exception_handler(
    ObligationNotFoundError, obligation_not_found_handler,
)
app.add_exception_handler(
    InvalidObligationStatusError, invalid_obligation_status_handler,
)

app.include_router(obligations_router)

logger.info('app started')
