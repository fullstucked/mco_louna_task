from typing import Annotated

from fastapi import Depends

from payments.application.handlers.commands.create import CreatePaymentUseCase


def create_payment_command() -> CreatePaymentUseCase:
    return CreatePaymentUseCase()


CreatePaymentDep = Annotated[
    CreatePaymentUseCase,
    Depends(create_payment_command),
]
