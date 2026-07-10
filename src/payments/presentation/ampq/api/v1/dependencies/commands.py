from payments.application.use_cases.events.process import ProcessPayment


def process_payment_command() -> ProcessPayment:
    return ProcessPayment()
