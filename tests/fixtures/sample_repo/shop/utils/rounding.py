"""Rounding helpers."""

from decimal import ROUND_HALF_UP, Decimal


def round_price(value, places=2):
    """Round a price half-up to the given number of decimal places."""
    quantum = Decimal(1).scaleb(-places)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))
