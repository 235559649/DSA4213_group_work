"""Pricing rules for the shop."""

from shop.utils.rounding import round_price

TAX_RATE = 0.09


def apply_discount(price, percent):
    """Return the price after a percentage discount."""
    return round_price(price * (1 - percent / 100))


class Cart:
    """A shopping cart holding (price, quantity) items."""

    currency = "SGD"

    def __init__(self):
        self.items = []
        self._discount = 0

    @property
    def discount(self):
        return self._discount

    @discount.setter
    def discount(self, value):
        self._discount = value

    def total(self, with_tax=True):
        """Total price of all items."""

        def line_total(item):
            price, quantity = item
            return price * quantity

        subtotal = sum(line_total(item) for item in self.items)
        if with_tax:
            subtotal *= 1 + TAX_RATE
        return round_price(subtotal)

    async def checkout(self, gateway):
        return await gateway.charge(self.total())

    class Receipt:
        def render(self):
            return "receipt"


if TAX_RATE > 0:

    def describe_tax():
        return f"GST {TAX_RATE:.0%}"

else:

    def describe_tax():
        return "no tax"
