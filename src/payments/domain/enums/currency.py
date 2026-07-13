from enum import Enum


class Currency(str, Enum):
    """
    Enumeration of supported payment currencies.
    Members:
        RUB: Russian Ruble
        USD: United States Dollar
        EUR: Euro
    """

    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
