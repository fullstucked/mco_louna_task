from fastapi import APIRouter, FastAPI

from payments.presentation.http.api.v1.routes.commands.create import command_router
from payments.presentation.http.api.v1.routes.queries.get_by_id import query_router


def register_routes(app: FastAPI):

    router = APIRouter(prefix="/v1/payments", tags=["payments"])

    router.include_router(command_router)
    router.include_router(query_router)
    app.include_router(router)
