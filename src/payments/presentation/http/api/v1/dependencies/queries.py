from typing import Annotated

from fastapi import Depends

from payments.application.use_cases.queries.get import GetPayment


def get_payment_query() -> GetPayment:
    return GetPayment()


GetPaymentDep = Annotated[
    GetPayment,
    Depends(get_payment_query),
]
