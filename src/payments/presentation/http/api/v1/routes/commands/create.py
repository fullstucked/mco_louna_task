from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, status

from payments.application.handlers.commands.create import (
    CreatePaymentCommand,
    CreatePaymentUseCase,
)
from payments.infrastructure.broker.event_bus import AMQPEventPublisher
from payments.infrastructure.database.uow import PaymentsUoWSQLAlchemy
from payments.presentation.http.api.v1.dependencies.commands import (
    create_payment_command,
)
from payments.presentation.http.api.v1.dependencies.infra.broker import get_publisher
from payments.presentation.http.api.v1.dependencies.infra.database import get_uow
from payments.presentation.http.api.v1.schemas.create import (
    CreatePaymentRequest,
    CreatePaymentResponse,
)

command_router = APIRouter(tags=["payments, commands"])


@command_router.post(
    "/",
    response_model=CreatePaymentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_payment(
    request: CreatePaymentRequest = Body(...),
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
    uc: CreatePaymentUseCase = Depends(create_payment_command),
    uow: PaymentsUoWSQLAlchemy = Depends(get_uow),
    publisher: AMQPEventPublisher = Depends(get_publisher),
):
    payment = await uc(
        command=CreatePaymentCommand(
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            metadata=request.metadata,
            webhook_url=str(request.webhook_url),
            key=idempotency_key,
        ),
        uow=uow,
        event_bus=publisher,
    )

    return CreatePaymentResponse.model_validate(payment)
