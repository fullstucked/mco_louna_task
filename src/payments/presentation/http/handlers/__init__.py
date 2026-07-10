from payments.presentation.http.handlers.exceptions.domain.errors import (
    register_shared_domain_exception_handlers,
)
from fastapi import FastAPI


def register_exceptions(app: FastAPI):
    (register_shared_domain_exception_handlers(app))
