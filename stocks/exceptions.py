class StockProjectError(Exception):
    """Base class of every stock project error."""


class NoTransactionError(StockProjectError):
    """No transaction in that day or period."""


class InvalidPriceError(Exception):
    """Price is invalid. Maybe your sell price goes beyond limit."""
