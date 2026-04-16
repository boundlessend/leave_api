from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppException(Exception):
    """базовая прикладная ошибка"""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: object | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    """обрабатывает прикладные ошибки"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    """обрабатывает ошибки валидации"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "ошибка валидации запроса",
                "details": jsonable_encoder(exc.errors()),
            }
        },
    )


async def unexpected_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """обрабатывает неожиданные ошибки"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "внутренняя ошибка сервера",
                "details": None,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """регистрирует обработчики ошибок"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )
    app.add_exception_handler(Exception, unexpected_exception_handler)
