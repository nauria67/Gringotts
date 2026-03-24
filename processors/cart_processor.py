import csv
import json
import os
from typing import List, Optional

from core.models.models import (
    AddCartItemsRequest,
    Cart,
    CartActivityLog,
    CartCreationRequest,
    CartEventType,
    CartItem,
    CartStatus,
    ObligationCreationRequest,
    ObligationOwnerType,
)
from processors.obligation_processor import ObligationProcessor


class CartProcessor:
    cart_activity_log_csv_path = (
        "/Users/obvio/Desktop/gringotts/data/cart_activity_log.csv"
    )
    cart_csv_path = "/Users/obvio/Desktop/gringotts/data/carts.csv"
    cart_item_csv_path = "/Users/obvio/Desktop/gringotts/data/cart_items.csv"
    _counter_file = "/Users/obvio/Desktop/gringotts/data/cart_id_counter.txt"
    _cart_item_counter_file = (
        "/Users/obvio/Desktop/gringotts/data/cart_item_id_counter.txt"
    )

    # Initialize the counter from the file or default to 1
    if os.path.exists(_counter_file):
        with open(_counter_file, "r") as file:
            _id_counter = int(file.read().strip())
    else:
        _id_counter = 1

    @staticmethod
    def _increment_counter():
        """Increment the counter and save it to the file."""
        CartProcessor._id_counter += 1
        with open(CartProcessor._counter_file, "w") as file:
            file.write(str(CartProcessor._id_counter))

    # Initialize the counter from the file or default to 1
    if os.path.exists(_cart_item_counter_file):
        with open(_cart_item_counter_file, "r") as file:
            _cart_item_id_counter = int(file.read().strip())
    else:
        _cart_item_id_counter = 1

    @staticmethod
    def _increment_cart_item_counter():
        """Increment the counter and save it to the file."""
        CartProcessor._cart_item_id_counter += 1
        with open(CartProcessor._cart_item_counter_file, "w") as file:
            file.write(str(CartProcessor._cart_item_id_counter))

    @staticmethod
    def store_cart_activity_log(cart_activity_log: CartActivityLog):
        """Store in csv"""
        file_exists = False
        try:
            with open(CartProcessor.cart_activity_log_csv_path, mode="r") as file:
                file_exists = True
        except FileNotFoundError:
            pass

        with open(
            CartProcessor.cart_activity_log_csv_path,
            mode="a",
            newline="",
        ) as file:
            writer = csv.writer(file)
            if not file_exists:
                # Write header row if the file is new
                writer.writerow(
                    [
                        "cart_id",
                        "old_status",
                        "new_status",
                        "event_type",
                        "amount",
                        "metadata",
                        "vendor_reference_id",
                        "vendor_reference_type",
                        "status_updated",
                        "vendor_event_id",
                    ]
                )

            writer.writerow(
                [
                    cart_activity_log.cart_id,
                    cart_activity_log.old_status,
                    cart_activity_log.new_status,
                    cart_activity_log.event_type,
                    cart_activity_log.amount,
                    (
                        json.dumps(cart_activity_log.metadata)
                        if cart_activity_log.metadata
                        else None
                    ),
                    cart_activity_log.vendor_reference_id,
                    cart_activity_log.vendor_reference_type,
                    cart_activity_log.status_updated,
                    cart_activity_log.vendor_event_id,
                ]
            )

    @staticmethod
    def store_cart(cart: Cart):
        """Store in CSV, add column names if it's a new file."""
        file_exists = False
        try:
            with open(CartProcessor.cart_csv_path, mode="r") as file:
                file_exists = True
        except FileNotFoundError:
            pass

        with open(CartProcessor.cart_csv_path, mode="a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:
                # Write header row if the file is new
                writer.writerow(["id", "amount", "vendor", "payment_mode", "status"])
            writer.writerow(
                [
                    cart.id,
                    cart.amount,
                    cart.vendor,
                    cart.payment_mode,
                    cart.status,
                ]
            )

    @staticmethod
    def store_cart_item(cart_item: CartItem):
        """Store in CSV, add column names if it's a new file."""
        file_exists = False
        try:
            with open(CartProcessor.cart_item_csv_path, mode="r") as file:
                file_exists = True
        except FileNotFoundError:
            pass

        with open(CartProcessor.cart_item_csv_path, mode="a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:
                # Write header row if the file is new
                writer.writerow(["id", "cart_id", "amount", "obligation_id"])
            writer.writerow(
                [
                    cart_item.id,
                    cart_item.cart_id,
                    cart_item.amount,
                    cart_item.obligation.id,
                ]
            )

    @staticmethod
    def update_cart(updated_cart: Cart):
        """Update an existing obligation in the CSV."""
        carts = []
        with open(CartProcessor.cart_csv_path, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if int(row["id"]) == updated_cart.id:
                    carts.append(updated_cart)  # Update the cart
                else:
                    carts.append(
                        Cart(
                            id=int(row["id"]),
                            amount=int(row["amount"]),
                            vendor=row["vendor"],
                            payment_mode=row["payment_mode"],
                            status=row["status"],
                        )
                    )

        with open(CartProcessor.cart_csv_path, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["id", "amount", "vendor", "payment_mode", "status"])

            for cart in carts:
                writer.writerow(
                    [
                        cart.id,
                        cart.amount,
                        cart.vendor,
                        cart.payment_mode,
                        cart.status,
                    ]
                )

    @staticmethod
    def read_carts() -> List[Cart]:
        """Read all carts from the CSV file."""
        carts = []
        with open(CartProcessor.cart_csv_path, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                carts.append(
                    Cart(
                        id=int(row["id"]),
                        amount=int(row["amount"]),
                        vendor=row["vendor"],
                        payment_mode=row["payment_mode"],
                        status=row["status"],
                    )
                )
        return carts

    @staticmethod
    def read_cart_items() -> List[CartItem]:
        """Read all cart items from the CSV file."""
        cart_items = []
        with open(CartProcessor.cart_item_csv_path, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                cart_items.append(
                    CartItem(
                        id=int(row["id"]),
                        cart_id=int(row["cart_id"]),
                        amount=int(row["amount"]),
                        obligation=ObligationProcessor.get_obligation_by_id(
                            obligation_id=int(row["obligation_id"])
                        ),
                    )
                )
        return cart_items

    @staticmethod
    def filter_cart_items(
        cart_items: List[CartItem], cart_id: Optional[int]
    ) -> List[CartItem]:
        """Filter cart items by cart ID."""
        if cart_id is None:
            return cart_items
        return [item for item in cart_items if item.cart_id == cart_id]

    @staticmethod
    def get_cart_by_id(cart_id: int) -> Cart:
        """Get a cart by its ID."""
        carts = CartProcessor.read_carts()
        for cart in carts:
            if cart.id == cart_id:
                filter_cart_items = CartProcessor.filter_cart_items(
                    CartProcessor.read_cart_items(), cart_id=cart.id
                )
                cart.cart_items = filter_cart_items
                return cart
        raise ValueError(f"Cart with ID {cart_id} not found.")

    @staticmethod
    def get_cart_item_by_id(cart_item_id: int) -> CartItem:
        """Get a cart item by its ID."""
        cart_items = CartProcessor.read_cart_items()
        for item in cart_items:
            if item.id == cart_item_id:
                return item
        raise ValueError(f"Cart item with ID {cart_item_id} not found.")

    @staticmethod
    def create_cart(
        cart_creation_request: CartCreationRequest,
        vendor_event_id: Optional[int] = None,
    ) -> Cart:
        """Create a cart from a cart creation request."""
        cart = Cart(
            id=CartProcessor._id_counter,
            amount=0,
            vendor=cart_creation_request.vendor,
            payment_mode=cart_creation_request.payment_mode,
            status=cart_creation_request.status,
            cart_items=[],
        )
        CartProcessor.store_cart(cart)
        CartProcessor._increment_counter()
        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            event_type=CartEventType.CREATED,
            old_status=None,
            new_status=cart.status,
            amount=cart.amount,
            status_updated=False,
            vendor_event_id=vendor_event_id,
        )
        CartProcessor.store_cart_activity_log(cart_activity_log)
        return cart

    @staticmethod
    def add_items_to_cart(
        add_cart_items_request: AddCartItemsRequest,
        vendor_event_id: Optional[int] = None,
    ) -> Cart:

        cart = add_cart_items_request.cart
        new_cart_items = []

        for payable in add_cart_items_request.cart_payables:
            obligation = ObligationProcessor.add_payable(
                ObligationCreationRequest(
                    type=payable.type,
                    amount=payable.amount,
                    owner_type=ObligationOwnerType.CART,
                    owner_id=cart.id,
                    status=payable.status,
                    label=payable.label,
                )
            )

            new_cart_items.append(
                CartItem(
                    cart_id=cart.id,
                    id=CartProcessor._cart_item_id_counter,
                    obligation=obligation,
                    amount=obligation.outstanding_amount,
                )
            )
            CartProcessor._increment_cart_item_counter()

        for obligation in add_cart_items_request.obligations:
            cart_item = CartItem(
                cart_id=cart.id,
                id=CartProcessor._cart_item_id_counter,
                obligation=obligation,
                amount=obligation.outstanding_amount,
            )
            new_cart_items.append(cart_item)
            CartProcessor._increment_cart_item_counter()

        for item in new_cart_items:
            CartProcessor.store_cart_item(item)
        cart.cart_items.extend(new_cart_items)
        cart.amount = sum(item.amount for item in cart.cart_items)
        CartProcessor.update_cart(cart)
        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.ITEMS_MODIFIED,
            old_status=cart.status,
            new_status=cart.status,
            vendor_event_id=vendor_event_id,
            status_updated=False,
        )
        CartProcessor.store_cart_activity_log(cart_activity_log)
        return cart

    @staticmethod
    def checkout_cart(cart: Cart) -> Cart:
        """Checkout the cart."""
        old_status = cart.status

        cart.status = CartStatus.CHECKOUT
        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.CHECKEDOUT,
            old_status=old_status,
            new_status=cart.status,
            status_updated=old_status != cart.status,
        )
        CartProcessor.store_cart_activity_log(cart_activity_log)
        return cart

    @staticmethod
    def submit_payment(cart: Cart) -> Cart:
        """Submit the cart for payment processing."""
        obligations = [item.obligation for item in cart.cart_items if item.obligation]
        print("obligations to lock:", obligations)
        ObligationProcessor.lock_obligations(
            cart.cart_items, lock_by=cart.id, payment_mode=cart.payment_mode
        )

        old_status = cart.status

        cart.status = CartStatus.PAYMENT_SUBMITTED
        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.STATUS_TRANSITIONED,
            old_status=old_status,
            new_status=cart.status,
            status_updated=old_status != cart.status,
        )
        CartProcessor.update_cart(cart)
        CartProcessor.store_cart_activity_log(cart_activity_log)
        return cart

    @staticmethod
    def settle_payment(cart: Cart, vendor_event_id: Optional[int] = None) -> Cart:
        """Settle` the payment for the cart."""
        old_status = cart.status

        cart.status = CartStatus.PAYMENT_SETTLED
        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.CART_SETTLED,
            old_status=old_status,
            new_status=cart.status,
            vendor_event_id=vendor_event_id,
            status_updated=old_status != cart.status,
        )
        CartProcessor.update_cart(cart)
        CartProcessor.store_cart_activity_log(cart_activity_log)
        return cart

    @staticmethod
    def confirm_payment(cart: Cart, vendor_event_id: Optional[int] = None) -> Cart:
        """Confirm the payment for the cart."""
        old_status = cart.status

        cart.status = CartStatus.PAYMENT_CONFIRMED
        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.CART_PAYMENT_CONFIRMED,
            old_status=old_status,
            new_status=cart.status,
            vendor_event_id=vendor_event_id,
            status_updated=old_status != cart.status,
        )
        CartProcessor.update_cart(cart)
        CartProcessor.store_cart_activity_log(cart_activity_log)
        return cart

    def mark_payment_dispute_funds_withdrawn(
        cart: Cart, vendor_event_id: Optional[int] = None
    ) -> Cart:
        """Mark the payment dispute funds as withdrawn for the cart."""
        old_status = cart.status
        cart.status = CartStatus.DISPUTED

        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.DISPUTE_FUNDS_WITHDRAWN,
            old_status=old_status,
            new_status=cart.status,
            vendor_event_id=vendor_event_id,
            status_updated=old_status != cart.status,
        )
        CartProcessor.update_cart(cart)
        CartProcessor.store_cart_activity_log(cart_activity_log)
        return cart

    def mark_payment_dispute_funds_returned(
        cart: Cart, vendor_event_id: Optional[int] = None
    ) -> Cart:
        """Mark the payment dispute funds as returned for the cart."""
        old_status = cart.status
        cart.status = CartStatus.PAYMENT_SETTLED

        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.DISPUTE_FUNDS_RETURNED,
            old_status=old_status,
            new_status=cart.status,
            vendor_event_id=vendor_event_id,
            status_updated=old_status != cart.status,
        )
        CartProcessor.update_cart(cart)
        CartProcessor.store_cart_activity_log(cart_activity_log)
        return cart

    def refund_payment(cart: Cart, vendor_event_id: Optional[int] = None) -> Cart:
        """Refund the payment for the cart."""

        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.CART_PAYMENT_REFUNDED,
            old_status=cart.status,
            new_status=cart.status,
            vendor_event_id=vendor_event_id,
            status_updated=False,
        )
        CartProcessor.store_cart_activity_log(cart_activity_log)
        return cart
