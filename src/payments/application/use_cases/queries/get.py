from payments.application.dto.queries.create import (
    GetPaymentQuery,
    GetPaymentQueryResponse,
)
from payments.application.interfaces.uow import PaymentUoW
from payments.domain.value_objects.id import PaymentID


class GetPayment:

    async def __call__(
        self,
        query: GetPaymentQuery,
        uow: PaymentUoW,
    ) -> GetPaymentQueryResponse:

        # Building value objects from command
        id = PaymentID(query.id)

        async with uow:
            # service = PaymentService(repo=uow.payments) # ERROR CHECK DDD APPROPRIATION AT NO USAGE OF SERVICE
            payment = await uow.payments.get_by_id(id)

        return GetPaymentQueryResponse.from_domain(payment)
