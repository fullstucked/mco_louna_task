from payments.application.interfaces.outbox_repository import PaymentEventRepository
from payments.domain.repository import PaymentRepository
from shared.application.interfaces.uow import AbstractUnitOfWork


class PaymentUoW(AbstractUnitOfWork):
    """
    Base interface for payment-related uow repos
    """

    payments: PaymentRepository
    outbox: PaymentEventRepository
