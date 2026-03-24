from datetime import datetime, timedelta, timezone

import pytest

from domain.cart.cart import Cart
from domain.cart.cart_item import CartItem
from domain.cart.enums import CartItemType, CartStatus, PaymentSource, PaymentType


def test_mark_as_paid_in_person():
    # to be called by api
    cart = Cart(
        status=CartStatus.PENDING,
        payment_type=PaymentType.CITATION_PAYMENT,
        payment_source=PaymentSource.IN_PERSON,
        customer_id="customer_1",
    )
    cart.add_item(
        CartItem(
            item_type=CartItemType.CITATION,
            identifier_type="citation_number",
            item_identifier="000001",
            customer_id="customer_1",
            amount=100,
        )
    )

    # to be called by treasury system

    cart.set_status(CartStatus.PAID)
    assert cart.status == CartStatus.PAID


def test_online_payment():
    # to be called by api
    cart = Cart(
        status=CartStatus.PENDING,
        payment_type=PaymentType.CITATION_PAYMENT,
        payment_source=PaymentSource.ONLINE,
        customer_id="customer_1",
    )
    cart.add_item(
        CartItem(
            item_type=CartItemType.CITATION,
            identifier_type="citation_number",
            item_identifier="000001",
            customer_id="customer_1",
            amount=100,
        )
    )

    # to be called by treasury system

    cart.set_status(CartStatus.PAID)
    assert cart.status == CartStatus.PAID


# Helper function to create a sample cart item
def create_cart_item(amount=100, customer_id="customer_1"):
    return CartItem(
        id=1,
        amount=amount,
        customer_id=customer_id,
        item_type="citation",
        identifier_type="citation_number",
        item_identifier="000001",
    )


def test_cart_creation():
    cart = Cart(
        id=1,
        status=CartStatus.PENDING,
        payment_type=PaymentType.CITATION_PAYMENT,
        payment_source=PaymentSource.ONLINE,
    )
    assert cart.id == 1
    assert cart.status == CartStatus.PENDING
    assert cart.total_amount == 0


def test_add_item():
    cart = Cart(
        id=1,
        status=CartStatus.PENDING,
        payment_type=PaymentType.CITATION_PAYMENT,
        payment_source=PaymentSource.ONLINE,
    )
    item = create_cart_item()
    cart.add_item(item)
    assert len(cart.items) == 1
    assert cart.total_amount == 100


def test_recompute_totals():
    cart = Cart(
        id=1,
        status=CartStatus.PENDING,
        payment_type=PaymentType.CITATION_PAYMENT,
        payment_source=PaymentSource.ONLINE,
    )
    item1 = create_cart_item(amount=100)
    item2 = create_cart_item(amount=200)
    cart.add_item(item1)
    cart.add_item(item2)
    cart.recompute_totals()
    assert cart.total_amount == 300


def test_cart_expiration():
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    cart = Cart(
        id=1,
        status=CartStatus.PENDING,
        payment_type=PaymentType.CITATION_PAYMENT,
        payment_source=PaymentSource.ONLINE,
        expires_at=expires_at,
    )
    assert not cart.is_expired()
    # Simulate expiration
    future_time = datetime.now(timezone.utc) + timedelta(minutes=10)
    assert cart.is_expired(now=future_time)


def test_infer_multi_customer():
    cart = Cart(
        id=1,
        status=CartStatus.PENDING,
        payment_type=PaymentType.CITATION_PAYMENT,
        payment_source=PaymentSource.ONLINE,
    )
    item1 = create_cart_item(customer_id="customer_1")
    item2 = create_cart_item(customer_id="customer_2")
    cart.add_item(item1)
    cart.add_item(item2)
    cart.infer_multi_customer()
    assert cart.is_multi_customer
    cart.add_item(item2)
    cart.infer_multi_customer()
    assert cart.is_multi_customer
