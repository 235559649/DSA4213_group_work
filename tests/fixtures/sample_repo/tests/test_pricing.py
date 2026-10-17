from shop.pricing import Cart, apply_discount


def test_apply_discount():
    assert apply_discount(100, 15) == 85.0


def test_empty_cart_total():
    assert Cart().total() == 0.0
