from uuid import UUID

from fastapi import APIRouter, Depends

from payments.application.dto.queries.create import GetPaymentQuery
from payments.application.use_cases.queries.get import GetPayment
from payments.infrastructure.database.uow import PaymentsUoWSQLAlchemy
from payments.presentation.http.api.v1.dependencies.infra.database import get_uow
from payments.presentation.http.api.v1.dependencies.queries import get_payment_query
from payments.presentation.http.api.v1.schemas.get import GetPaymentResponse

query_router = APIRouter(tags=["payments, queries"])


@query_router.get(
    "/{payment_id}",
    response_model=GetPaymentResponse,
)
async def get_payment(
    payment_id: UUID,
    uc: GetPayment = Depends(get_payment_query),
    uow: PaymentsUoWSQLAlchemy = Depends(get_uow),
):
    payment = await uc(
        query=GetPaymentQuery(id=payment_id),
        uow=uow,
    )

    return GetPaymentResponse.model_validate(payment)
