from typing import cast

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    InvalidObligationStatusError,
    ObligationNotFoundError,
)


async def invalid_obligation_status_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Обрабатывает ответ для ошибки 422."""
    error = cast(InvalidObligationStatusError, exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            'detail': str(error),
        },
    )


async def obligation_not_found_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Обрабатывает ответ для ошибки 404."""
    error = cast(ObligationNotFoundError, exc)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            'detail': str(error),
        },
    )
