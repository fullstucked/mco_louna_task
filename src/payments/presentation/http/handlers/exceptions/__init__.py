from fastapi import FastAPI

from payments.presentation.http.handlers.exceptions.application.interfaces import (
    register_application_exception_handlers,
)
from payments.presentation.http.handlers.exceptions.domain.errors import (
    register_shared_domain_exception_handlers,
)
from payments.presentation.http.handlers.exceptions.shared.runtime import (
    register_runtime_exception_handlers,
)


def register_exceptions(app: FastAPI):
    register_shared_domain_exception_handlers(app)
    register_application_exception_handlers(app)
    register_runtime_exception_handlers(app)
