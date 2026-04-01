import csv
import json
import os
from typing import Any, List, Optional

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
    PaymentMode,
    VendorName,
)
from processors.log_manager import AuditLogManager
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

    if os.path.exists(_counter_file):
        with open(_counter_file, "r") as file:
            _id_counter = int(file.read().strip())
    else:
        _id_counter = 1

    if os.path.exists(_cart_item_counter_file):
        with open(_cart_item_counter_file, "r") as file:
            _cart_item_id_counter = int(file.read().strip())
    else:
        _cart_item_id_counter = 1

    @staticmethod
    def _increment_counter():
        CartProcessor._id_counter += 1
        with open(CartProcessor._counter_file, "w") as file:
            file.write(str(CartProcessor._id_counter))

    @staticmethod
    def _increment_cart_item_counter():
        CartProcessor._cart_item_id_counter += 1
        with open(CartProcessor._cart_item_counter_file, "w") as file:
            file.write(str(CartProcessor._cart_item_id_counter))

    @staticmethod
    def _get_ctx_value(
        audit_context: Optional[dict[str, Any]], key: str
    ) -> Optional[str]:
        if not audit_context:
            return None
        value = audit_context.get(key)
        return str(value) if value is not None else None

    @staticmethod
    def _enum_value(value):
        return value.value if value is not None else None

    @staticmethod
    def _cart_snapshot(cart: Cart) -> dict[str, Any]:
        return {
            "id": cart.id,
            "amount": cart.amount,
            "refund_amount": cart.refund_amount,
            "vendor": cart.vendor.value,
            "payment_mode": cart.payment_mode.value if cart.payment_mode else None,
            "status": cart.status.value if cart.status else None,
            "cart_items": [
                {
                    "id": item.id,
                    "cart_id": item.cart_id,
                    "amount": item.amount,
                    "obligation_id": item.obligation.id if item.obligation else None,
                    "obligation_label": (
                        item.obligation.label if item.obligation else None
                    ),
                }
                for item in (cart.cart_items or [])
            ],
        }

    @staticmethod
    def _log_cart_audit(
        *,
        action: str,
        cart: Cart,
        old_status: Optional[str],
        new_status: Optional[str],
        amount: Optional[int],
        before_snapshot: Optional[dict[str, Any]],
        after_snapshot: Optional[dict[str, Any]],
        audit_context: Optional[dict[str, Any]] = None,
        vendor_event_id: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        status: str = "success",
        reason: Optional[str] = None,
    ) -> None:
        AuditLogManager.log_event(
            domain="cart",
            action=action,
            entity_type="cart",
            entity_id=str(cart.id),
            actor_type=CartProcessor._get_ctx_value(audit_context, "actor_type")
            or "system",
            actor_id=CartProcessor._get_ctx_value(audit_context, "actor_id"),
            source=CartProcessor._get_ctx_value(audit_context, "source")
            or "cart_processor",
            request_id=CartProcessor._get_ctx_value(audit_context, "request_id"),
            correlation_id=CartProcessor._get_ctx_value(
                audit_context, "correlation_id"
            ),
            causation_id=CartProcessor._get_ctx_value(audit_context, "causation_id"),
            cart_id=cart.id,
            vendor_event_id=vendor_event_id,
            old_status=CartProcessor._enum_value(old_status),
            new_status=CartProcessor._enum_value(new_status),
            amount=amount,
            status=status,
            reason=reason,
            before_snapshot=before_snapshot or {},
            after_snapshot=after_snapshot or {},
            metadata=metadata or {},
        )

    @staticmethod
    def store_cart_activity_log(cart_activity_log: CartActivityLog):
        file_exists = False
        try:
            with open(CartProcessor.cart_activity_log_csv_path, mode="r"):
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
        file_exists = False
        try:
            with open(CartProcessor.cart_csv_path, mode="r"):
                file_exists = True
        except FileNotFoundError:
            pass

        with open(CartProcessor.cart_csv_path, mode="a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(
                    [
                        "id",
                        "amount",
                        "refund_amount",
                        "vendor",
                        "payment_mode",
                        "status",
                    ]
                )
            writer.writerow(
                [
                    cart.id,
                    cart.amount,
                    cart.refund_amount,
                    cart.vendor,
                    cart.payment_mode,
                    cart.status,
                ]
            )

    @staticmethod
    def store_cart_item(cart_item: CartItem):
        file_exists = False
        try:
            with open(CartProcessor.cart_item_csv_path, mode="r"):
                file_exists = True
        except FileNotFoundError:
            pass

        with open(CartProcessor.cart_item_csv_path, mode="a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:
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
        carts = []
        with open(CartProcessor.cart_csv_path, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if int(row["id"]) == updated_cart.id:
                    carts.append(updated_cart)
                else:
                    carts.append(
                        Cart(
                            id=int(row["id"]),
                            amount=int(row["amount"]),
                            refund_amount=int(row.get("refund_amount") or 0),
                            vendor=VendorName(row["vendor"]),
                            payment_mode=PaymentMode(row["payment_mode"]),
                            status=CartStatus(row["status"]),
                        )
                    )

        with open(CartProcessor.cart_csv_path, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                ["id", "amount", "refund_amount", "vendor", "payment_mode", "status"]
            )

            for cart in carts:
                writer.writerow(
                    [
                        cart.id,
                        cart.amount,
                        cart.refund_amount,
                        cart.vendor,
                        cart.payment_mode,
                        cart.status,
                    ]
                )

    @staticmethod
    def read_carts() -> List[Cart]:
        carts = []
        with open(CartProcessor.cart_csv_path, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                carts.append(
                    Cart(
                        id=int(row["id"]),
                        amount=int(row["amount"]),
                        refund_amount=int(row.get("refund_amount") or 0),
                        vendor=VendorName(row["vendor"]),
                        payment_mode=(
                            PaymentMode(row["payment_mode"])
                            if row["payment_mode"]
                            else None
                        ),
                        status=CartStatus(row["status"]) if row["status"] else None,
                    )
                )
        return carts

    @staticmethod
    def read_cart_items() -> List[CartItem]:
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
        if cart_id is None:
            return cart_items
        return [item for item in cart_items if item.cart_id == cart_id]

    @staticmethod
    def get_cart_by_id(cart_id: int) -> Cart:
        carts = CartProcessor.read_carts()
        for cart in carts:
            if cart.id == cart_id:
                filtered_cart_items = CartProcessor.filter_cart_items(
                    CartProcessor.read_cart_items(), cart_id=cart.id
                )
                cart.cart_items = filtered_cart_items
                return cart
        raise ValueError(f"Cart with ID {cart_id} not found.")

    @staticmethod
    def get_cart_item_by_id(cart_item_id: int) -> CartItem:
        cart_items = CartProcessor.read_cart_items()
        for item in cart_items:
            if item.id == cart_item_id:
                return item
        raise ValueError(f"Cart item with ID {cart_item_id} not found.")

    @staticmethod
    def create_cart(
        cart_creation_request: CartCreationRequest,
        vendor_event_id: Optional[int] = None,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Cart:
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

        CartProcessor._log_cart_audit(
            action="cart.created",
            cart=cart,
            old_status=None,
            new_status=cart.status,
            amount=cart.amount,
            before_snapshot={},
            after_snapshot=CartProcessor._cart_snapshot(cart),
            audit_context=audit_context,
            vendor_event_id=vendor_event_id,
            metadata={"event_type": CartEventType.CREATED.value},
        )
        return cart

    @staticmethod
    def add_items_to_cart(
        add_cart_items_request: AddCartItemsRequest,
        vendor_event_id: Optional[int] = None,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Cart:
        cart = add_cart_items_request.cart
        before_snapshot = CartProcessor._cart_snapshot(cart)
        new_cart_items = []

        for payable in add_cart_items_request.cart_payables:
            obligation = ObligationProcessor.add_payable(
                request=ObligationCreationRequest(
                    type=payable.type,
                    amount=payable.amount,
                    owner_type=ObligationOwnerType.CART,
                    owner_id=cart.id,
                    status=payable.status,
                    label=payable.label,
                ),
                audit_context=audit_context,
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

        CartProcessor._log_cart_audit(
            action="cart.items_added",
            cart=cart,
            old_status=cart.status,
            new_status=cart.status,
            amount=cart.amount,
            before_snapshot=before_snapshot,
            after_snapshot=CartProcessor._cart_snapshot(cart),
            audit_context=audit_context,
            vendor_event_id=vendor_event_id,
            metadata={
                "event_type": CartEventType.ITEMS_MODIFIED.value,
                "new_cart_item_ids": [item.id for item in new_cart_items],
                "new_obligation_ids": [
                    item.obligation.id for item in new_cart_items if item.obligation
                ],
            },
        )
        return cart

    @staticmethod
    def checkout_cart(
        cart: Cart,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Cart:
        old_status = cart.status
        before_snapshot = CartProcessor._cart_snapshot(cart)

        cart.status = CartStatus.CHECKOUT
        CartProcessor.update_cart(cart)

        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.CHECKEDOUT,
            old_status=old_status,
            new_status=cart.status,
            status_updated=old_status != cart.status,
        )
        CartProcessor.store_cart_activity_log(cart_activity_log)

        CartProcessor._log_cart_audit(
            action="cart.checked_out",
            cart=cart,
            old_status=old_status,
            new_status=cart.status,
            amount=cart.amount,
            before_snapshot=before_snapshot,
            after_snapshot=CartProcessor._cart_snapshot(cart),
            audit_context=audit_context,
            metadata={"event_type": CartEventType.CHECKEDOUT.value},
        )
        return cart

    @staticmethod
    def submit_payment(
        cart: Cart,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Cart:
        obligations = [item.obligation for item in cart.cart_items if item.obligation]
        print("obligations to lock:", obligations)

        before_snapshot = CartProcessor._cart_snapshot(cart)
        old_status = cart.status

        ObligationProcessor.lock_obligations(
            cart.cart_items,
            lock_by=cart.id,
            payment_mode=cart.payment_mode,
            audit_context=audit_context,
        )

        cart.status = CartStatus.PAYMENT_SUBMITTED
        CartProcessor.update_cart(cart)

        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.PAYMENT_SUBMITTED,
            old_status=old_status,
            new_status=cart.status,
            status_updated=old_status != cart.status,
        )
        CartProcessor.store_cart_activity_log(cart_activity_log)

        CartProcessor._log_cart_audit(
            action="cart.payment_submitted",
            cart=cart,
            old_status=old_status,
            new_status=cart.status,
            amount=cart.amount,
            before_snapshot=before_snapshot,
            after_snapshot=CartProcessor._cart_snapshot(cart),
            audit_context=audit_context,
            metadata={
                "event_type": CartEventType.PAYMENT_SUBMITTED.value,
                "locked_obligation_ids": [o.id for o in obligations],
            },
        )
        return cart

    @staticmethod
    def settle_payment(
        cart: Cart,
        vendor_event_id: Optional[int] = None,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Cart:
        old_status = cart.status
        before_snapshot = CartProcessor._cart_snapshot(cart)

        cart.status = CartStatus.PAYMENT_SETTLED
        CartProcessor.update_cart(cart)

        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.CART_SETTLED,
            old_status=old_status,
            new_status=cart.status,
            vendor_event_id=vendor_event_id,
            status_updated=old_status != cart.status,
        )
        CartProcessor.store_cart_activity_log(cart_activity_log)

        CartProcessor._log_cart_audit(
            action="cart.payment_settled",
            cart=cart,
            old_status=old_status,
            new_status=cart.status,
            amount=cart.amount,
            before_snapshot=before_snapshot,
            after_snapshot=CartProcessor._cart_snapshot(cart),
            audit_context=audit_context,
            vendor_event_id=vendor_event_id,
            metadata={"event_type": CartEventType.CART_SETTLED.value},
        )
        return cart

    @staticmethod
    def confirm_payment(
        cart: Cart,
        vendor_event_id: Optional[int] = None,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Cart:
        old_status = cart.status
        before_snapshot = CartProcessor._cart_snapshot(cart)

        cart.status = CartStatus.PAYMENT_CONFIRMED
        CartProcessor.update_cart(cart)

        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.CART_PAYMENT_CONFIRMED,
            old_status=old_status,
            new_status=cart.status,
            vendor_event_id=vendor_event_id,
            status_updated=old_status != cart.status,
        )
        CartProcessor.store_cart_activity_log(cart_activity_log)

        CartProcessor._log_cart_audit(
            action="cart.payment_confirmed",
            cart=cart,
            old_status=old_status,
            new_status=cart.status,
            amount=cart.amount,
            before_snapshot=before_snapshot,
            after_snapshot=CartProcessor._cart_snapshot(cart),
            audit_context=audit_context,
            vendor_event_id=vendor_event_id,
            metadata={"event_type": CartEventType.CART_PAYMENT_CONFIRMED.value},
        )
        return cart

    @staticmethod
    def mark_payment_dispute_funds_withdrawn(
        cart: Cart,
        vendor_event_id: Optional[int] = None,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Cart:
        old_status = cart.status
        before_snapshot = CartProcessor._cart_snapshot(cart)

        cart.status = CartStatus.DISPUTED
        CartProcessor.update_cart(cart)

        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.DISPUTE_FUNDS_WITHDRAWN,
            old_status=old_status,
            new_status=cart.status,
            vendor_event_id=vendor_event_id,
            status_updated=old_status != cart.status,
        )
        CartProcessor.store_cart_activity_log(cart_activity_log)

        CartProcessor._log_cart_audit(
            action="cart.dispute_funds_withdrawn",
            cart=cart,
            old_status=old_status,
            new_status=cart.status,
            amount=cart.amount,
            before_snapshot=before_snapshot,
            after_snapshot=CartProcessor._cart_snapshot(cart),
            audit_context=audit_context,
            vendor_event_id=vendor_event_id,
            metadata={"event_type": CartEventType.DISPUTE_FUNDS_WITHDRAWN.value},
        )
        return cart

    @staticmethod
    def mark_payment_dispute_funds_returned(
        cart: Cart,
        vendor_event_id: Optional[int] = None,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Cart:
        old_status = cart.status
        before_snapshot = CartProcessor._cart_snapshot(cart)

        cart.status = CartStatus.PAYMENT_SETTLED
        CartProcessor.update_cart(cart)

        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.DISPUTE_FUNDS_RETURNED,
            old_status=old_status,
            new_status=cart.status,
            vendor_event_id=vendor_event_id,
            status_updated=old_status != cart.status,
        )
        CartProcessor.store_cart_activity_log(cart_activity_log)

        CartProcessor._log_cart_audit(
            action="cart.dispute_funds_returned",
            cart=cart,
            old_status=old_status,
            new_status=cart.status,
            amount=cart.amount,
            before_snapshot=before_snapshot,
            after_snapshot=CartProcessor._cart_snapshot(cart),
            audit_context=audit_context,
            vendor_event_id=vendor_event_id,
            metadata={"event_type": CartEventType.DISPUTE_FUNDS_RETURNED.value},
        )
        return cart

    @staticmethod
    def refund_payment(
        cart: Cart,
        refund_amount: int,
        vendor_event_id: Optional[int] = None,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Cart:
        before_snapshot = CartProcessor._cart_snapshot(cart)

        cart.refund_amount = (cart.refund_amount or 0) + refund_amount
        CartProcessor.update_cart(cart)

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

        CartProcessor._log_cart_audit(
            action="cart.payment_refunded",
            cart=cart,
            old_status=cart.status,
            new_status=cart.status,
            amount=refund_amount,
            before_snapshot=before_snapshot,
            after_snapshot=CartProcessor._cart_snapshot(cart),
            audit_context=audit_context,
            vendor_event_id=vendor_event_id,
            metadata={
                "event_type": CartEventType.CART_PAYMENT_REFUNDED.value,
                "refund_amount": refund_amount,
                "total_refund_amount": cart.refund_amount,
            },
        )
        return cart

    @staticmethod
    def mark_dispute_lost(
        cart: Cart,
        vendor_event_id: Optional[int] = None,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Cart:
        old_status = cart.status
        before_snapshot = CartProcessor._cart_snapshot(cart)

        cart.status = CartStatus.DISPUTE_LOST
        CartProcessor.update_cart(cart)

        cart_activity_log = CartActivityLog(
            cart_id=cart.id,
            amount=cart.amount,
            event_type=CartEventType.DISPUTE_LOST,
            old_status=old_status,
            new_status=cart.status,
            vendor_event_id=vendor_event_id,
            status_updated=True,
        )
        CartProcessor.store_cart_activity_log(cart_activity_log)

        CartProcessor._log_cart_audit(
            action="cart.dispute_lost",
            cart=cart,
            old_status=old_status,
            new_status=cart.status,
            amount=cart.amount,
            before_snapshot=before_snapshot,
            after_snapshot=CartProcessor._cart_snapshot(cart),
            audit_context=audit_context,
            vendor_event_id=vendor_event_id,
            metadata={"event_type": CartEventType.DISPUTE_LOST.value},
        )
        return cart
