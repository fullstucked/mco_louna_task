from fastapi import Depends, FastAPI

from payments.presentation.http.api.v1.router import register_routes
from payments.presentation.http.dependencies.auth.api_key import get_api_key
from payments.presentation.http.handlers.exceptions import register_exceptions
from payments.presentation.http.lifespan import lifespan


def create_app() -> FastAPI:
    app = FastAPI(
        title="Async payment processing service",
        version="0.0.1",
        lifespan=lifespan,
        dependencies=[Depends(get_api_key)],
    )

    register_exceptions(app)
    register_routes(app)

    return app
