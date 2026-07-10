from fastapi import FastAPI, Request, status
from starlette.responses import JSONResponse

from shared.domain.errors import (
    DomainBusinessRuleError,
    DomainInvariantError,
    DomainResourceNotFoundError,
)


def register_shared_domain_exception_handlers(app: FastAPI):

    @app.exception_handler(DomainResourceNotFoundError)
    async def generic_not_found_error(request: Request, exc: Exception):
        return JSONResponse(content={"error": {"message": "not found!"}})

    @app.exception_handler(DomainBusinessRuleError)
    async def business_rule_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"type": "internal server error"}},
        )

    @app.exception_handler(DomainInvariantError)
    async def generic_business_rule_error_handler(
        request: Request, exc: DomainInvariantError
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"type": "wrong input", "message": str(exc)}},
        )
