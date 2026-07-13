from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from payments.application.interfaces.uow import (
    RepositoriesExhaustedError,
    RepositoriesUnavailableError,
)


def register_application_exception_handlers(app: FastAPI):
    """
    Register application-layer exception handlers.
    Maps repository exceptions to appropriate HTTP responses.
    """

    @app.exception_handler(RepositoriesUnavailableError)
    async def database_unavailable_error(
        request: Request,
        exc: RepositoriesUnavailableError,
    ) -> JSONResponse:
        """
        Database is unavailable or connection lost.
        Clients should retry with exponential backoff.
        """
        return JSONResponse(
            content={
                "error": {
                    "message": "Database service temporarily unavailable",
                    "details": "The payment service cannot reach the database. Please retry in a few moments.",
                    "error_code": "REPOSITORY_UNAVAILABLE",
                }
            },
            status_code=503,
        )

    @app.exception_handler(RepositoriesExhaustedError)
    async def connection_pool_exhausted_error(
        request: Request,
        exc: RepositoriesExhaustedError,
    ) -> JSONResponse:
        """
        Connection pool exhausted; no available connections.
        Service is overloaded; clients should retry with backoff.
        """
        return JSONResponse(
            content={
                "error": {
                    "message": "Service overloaded, too many concurrent requests",
                    "details": "The payment service is processing too many requests. Please retry in a few moments.",
                    "error_code": "REPOSITORY_EXHAUSTED",
                }
            },
            status_code=503,
        )
