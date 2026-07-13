

from payments.application.handlers.events.process import ProcessPayment


def process_payment_command() -> ProcessPayment:
    return ProcessPayment()
