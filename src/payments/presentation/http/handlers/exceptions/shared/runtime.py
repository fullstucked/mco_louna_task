from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from structlog import get_logger

logger = get_logger()


def register_runtime_exception_handlers(app: FastAPI):
    """Register handlers for standard Python runtime exceptions."""

    @app.exception_handler(TypeError)
    async def type_error_handler(request: Request, exc: TypeError) -> JSONResponse:
        """Type mismatch or invalid operation on wrong type."""

        # logger.warning(
        #     "TypeError",
        #     extra={"path": request.url.path, "error": str(exc)},
        # )

        return JSONResponse(
            content={
                "error": {
                    "message": "Invalid argument type",
                    "details": str(exc),
                    "error_code": "TYPE_ERROR",
                }
            },
            status_code=400,
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Invalid value for operation."""

        # logger.warning(
        #     "ValueError",
        #     extra={"path": request.url.path, "error": str(exc)},
        # )

        return JSONResponse(
            content={
                "error": {
                    "message": "Invalid argument value",
                    "details": str(exc),
                    "error_code": "VALUE_ERROR",
                }
            },
            status_code=400,
        )

    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError) -> JSONResponse:
        """Dictionary/mapping key not found."""

        # logger.info(
        #     "KeyError",
        #     extra={"path": request.url.path, "key": str(exc.args[0])},
        # )

        return JSONResponse(
            content={
                "error": {
                    "message": "Required field missing",
                    "details": f"Missing key: {exc.args[0]}",
                    "error_code": "MISSING_FIELD",
                }
            },
            status_code=400,
        )

    @app.exception_handler(AttributeError)
    async def attribute_error_handler(
        request: Request, exc: AttributeError
    ) -> JSONResponse:
        """Object attribute not found."""

        # logger.error(
        #     "AttributeError",
        #     extra={"path": request.url.path, "error": str(exc)},
        # )

        return JSONResponse(
            content={
                "error": {
                    "message": "Internal attribute error",
                    "details": "Service misconfiguration detected.",
                    "error_code": "INTERNAL_ERROR",
                }
            },
            status_code=500,
        )

    @app.exception_handler(IndexError)
    async def index_error_handler(request: Request, exc: IndexError) -> JSONResponse:
        """List/sequence index out of range."""

        # logger.warning(
        #     "IndexError",
        #     extra={"path": request.url.path, "error": str(exc)},
        # )

        return JSONResponse(
            content={
                "error": {
                    "message": "Index out of range",
                    "details": str(exc),
                    "error_code": "INDEX_ERROR",
                }
            },
            status_code=400,
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(
        request: Request, exc: RuntimeError
    ) -> JSONResponse:
        """Generic runtime error."""

        # logger.error(
        #     "RuntimeError",
        #     extra={"path": request.url.path, "error": str(exc)},
        # )

        return JSONResponse(
            content={
                "error": {
                    "message": "Runtime error",
                    "details": str(exc),
                    "error_code": "RUNTIME_ERROR",
                }
            },
            status_code=500,
        )

    @app.exception_handler(TimeoutError)
    async def timeout_error_handler(
        request: Request, exc: TimeoutError
    ) -> JSONResponse:
        """Operation timed out."""

        # logger.warning(
        #     "TimeoutError",
        #     extra={"path": request.url.path, "error": str(exc)},
        # )

        return JSONResponse(
            content={
                "error": {
                    "message": "Operation timed out",
                    "details": "Request took too long. Please retry.",
                    "error_code": "TIMEOUT",
                }
            },
            status_code=408,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all for unhandled exceptions."""

        # logger.exception(
        #     "Unhandled exception",
        #     extra={"path": request.url.path, "error_type": type(exc).__name__},
        # )

        return JSONResponse(
            content={
                "error": {
                    "message": "Internal server error",
                    "details": "An unexpected error occurred. Please contact support.",
                    "error_code": "INTERNAL_ERROR",
                }
            },
            status_code=500,
        )
