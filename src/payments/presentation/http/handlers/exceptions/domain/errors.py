from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from shared.domain.enums.scope import Scope
from shared.domain.errors import (
    DomainBusinessRuleError,
    DomainInvariantError,
    DomainResourceExistsError,
    DomainResourceNotFoundError,
)


def register_shared_domain_exception_handlers(app: FastAPI):

    @app.exception_handler(DomainResourceNotFoundError)
    async def generic_not_found_error(
        request: Request,
        exc: DomainResourceNotFoundError,
    ):
        return JSONResponse(
            content={
                "error": {
                    "message": exc.message,
                    "details": (
                        exc.context["details"] if exc.scope == Scope.public else ""
                    ),
                }
            },
            status_code=exc.context["status"],
        )

    @app.exception_handler(DomainBusinessRuleError)
    async def business_rule_error_handler(
        request: Request,
        exc: DomainBusinessRuleError,
    ):
        return JSONResponse(
            content={
                "error": {
                    "message": exc.message,
                    "details": (
                        exc.context["details"] if exc.scope == Scope.public else ""
                    ),
                }
            },
            status_code=exc.context["status"],
        )

    @app.exception_handler(DomainInvariantError)
    async def invariant_error_handler(
        request: Request,
        exc: DomainBusinessRuleError,
    ):
        return JSONResponse(
            content={
                "error": {
                    "message": exc.message,
                    "details": (
                        exc.context["details"] if exc.scope == Scope.public else ""
                    ),
                }
            },
            status_code=exc.context["status"],
        )

    @app.exception_handler(DomainResourceExistsError)
    async def exists_error_handler(
        request: Request,
        exc: DomainResourceExistsError,
    ):
        return JSONResponse(
            content={
                "error": {
                    "message": exc.message,
                    "details": (
                        exc.context["details"] if exc.scope == Scope.public else ""
                    ),
                }
            },
            status_code=exc.context["status"],
        )
