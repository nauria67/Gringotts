import time
from dataclasses import dataclass
from typing import Any, Optional

from core.models.models import (
    AddCartItemsRequest,
    Cart,
    CartCreationRequest,
    CartItem,
    CartStatus,
    LedgerAllocationItemInput,
    Obligation,
    TransactionAllocationType,
    TransactionItemAllocation,
    VendorEvent,
    VendorEventType,
    VendorName,
)
from processors.cart_processor import CartProcessor
from processors.ledger import Ledger
from processors.obligation_processor import ObligationProcessor


@dataclass
class ResolvedAllocation:
    obligation: Obligation
    cart_item: Optional[CartItem]
    amount: float


class PaymentOrchestrator:
    @staticmethod
    def _resolve_vendor_event_allocation_to_obligation(
        allocation: TransactionItemAllocation,
        cart: Optional[Cart],
    ) -> ResolvedAllocation:
        """
        First pass:
        Resolve every incoming allocation to an obligation.
        cart_item may or may not be available at this stage.
        """
        if allocation.allocation_type == TransactionAllocationType.CART_ITEM:
            if not cart:
                raise Exception("Cart is required when allocation_type is CART_ITEM")

            cart_item_id = allocation.cart_item_id
            cart_item = next(
                (item for item in (cart.cart_items or []) if item.id == cart_item_id),
                None,
            )
            if not cart_item:
                raise Exception(f"No cart item found for cart_item_id={cart_item_id}")

            return ResolvedAllocation(
                obligation=cart_item.obligation,
                cart_item=cart_item,
                amount=allocation.amount,
            )

        if allocation.allocation_type == TransactionAllocationType.PAYABLE:
            obligation = ObligationProcessor.get_valid_obligation_against_payable(
                owner_id=allocation.owner_id,
                owner_type=allocation.owner_type,
                label=allocation.label,
            )
            if not obligation:
                raise Exception(
                    "No valid obligation found for "
                    f"owner_id={allocation.owner_id}, "
                    f"owner_type={allocation.owner_type}, "
                    f"label={allocation.label}"
                )

            return ResolvedAllocation(
                obligation=obligation,
                cart_item=None,
                amount=allocation.amount,
            )

        raise Exception(f"Unsupported allocation type: {allocation.allocation_type}")

    @staticmethod
    def _attach_cart_items_to_resolved_allocations(
        allocations: list[ResolvedAllocation],
        cart: Cart,
    ) -> list[ResolvedAllocation]:
        """
        Second pass:
        Ensure every resolved allocation has a cart_item.
        Useful after cart creation for PAYABLE allocations.
        """
        resolved_allocations: list[ResolvedAllocation] = []

        for allocation in allocations:
            if allocation.cart_item is not None:
                resolved_allocations.append(allocation)
                continue

            matching_cart_item = next(
                (
                    item
                    for item in (cart.cart_items or [])
                    if item.obligation.id == allocation.obligation.id
                ),
                None,
            )

            if not matching_cart_item:
                raise Exception(
                    "No cart item found for obligation_id="
                    f"{allocation.obligation.id}"
                )

            resolved_allocations.append(
                ResolvedAllocation(
                    obligation=allocation.obligation,
                    cart_item=matching_cart_item,
                    amount=allocation.amount,
                )
            )

        return resolved_allocations

    @staticmethod
    def process_payment_event(
        vendor_event: VendorEvent,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> list[LedgerAllocationItemInput]:
        cart = vendor_event.cart
        transaction = vendor_event.transaction

        if not transaction:
            raise Exception("Vendor event must contain a transaction")

        raw_allocations = transaction.item_allocations or []
        print("Raw allocations from transaction:", raw_allocations)

        # Pass 1: resolve all incoming allocations to obligations
        resolved_allocations = [
            PaymentOrchestrator._resolve_vendor_event_allocation_to_obligation(
                allocation=allocation,
                cart=cart,
            )
            for allocation in raw_allocations
        ]

        # If cart does not exist, create it from resolved obligations
        if not cart:
            obligation_list = [
                allocation.obligation for allocation in resolved_allocations
            ]

            cart = CartProcessor.create_cart(
                CartCreationRequest(
                    status=CartStatus.SYSTEM_CREATED,
                    vendor=VendorName.CHECKALT,
                    payment_mode=vendor_event.payment_mode,
                ),
                audit_context=audit_context,
            )

            cart = CartProcessor.add_items_to_cart(
                AddCartItemsRequest(
                    cart=cart,
                    obligations=obligation_list,
                ),
                audit_context=audit_context,
            )

        # Pass 2: ensure every allocation now has a cart_item
        resolved_allocations = (
            PaymentOrchestrator._attach_cart_items_to_resolved_allocations(
                allocations=resolved_allocations,
                cart=cart,
            )
        )

        # Defensive validation before ledger
        missing_cart_items = [
            allocation
            for allocation in resolved_allocations
            if allocation.cart_item is None
        ]
        if missing_cart_items:
            raise Exception(
                "All resolved allocations must have cart_item before sending to ledger"
            )

        ledger_allocation_item_inputs = [
            LedgerAllocationItemInput(
                cart_item=allocation.cart_item,
                amount=allocation.amount,
            )
            for allocation in resolved_allocations
        ]
        print(
            "Resolved allocations to be sent to ledger:", ledger_allocation_item_inputs
        )

        ledger_items = Ledger.record_event(
            vendor_event=vendor_event,
            cart=cart,
            item_allocations=ledger_allocation_item_inputs,
            record_time=int(time.time() * 1000),
            audit_context=audit_context,
        )

        if vendor_event.event_type == VendorEventType.PAYMENT_SETTLED:
            CartProcessor.settle_payment(cart, audit_context=audit_context)
        elif vendor_event.event_type == VendorEventType.PAYMENT_CONFIRMED:
            CartProcessor.confirm_payment(cart, audit_context=audit_context)
        elif vendor_event.event_type == VendorEventType.PAYMENT_REFUNDED:
            CartProcessor.refund_payment(
                cart,
                refund_amount=transaction.amount,
                vendor_event_id=vendor_event.id,
                audit_context=audit_context,
            )
        elif vendor_event.event_type == VendorEventType.PAYMENT_DISPUTE_FUNDS_WITHDRAWN:
            CartProcessor.mark_payment_dispute_funds_withdrawn(
                cart, audit_context=audit_context
            )
        elif vendor_event.event_type == VendorEventType.PAYMENT_DISPUTE_FUNDS_RETURNED:
            CartProcessor.mark_payment_dispute_funds_returned(
                cart, audit_context=audit_context
            )
        for ledger_item in ledger_items:
            allocations = ledger_item.allocations or []
            for allocation in allocations:
                obligation = allocation.cart_item.obligation
                obligation = ObligationProcessor.update_obligation_according_to_ledger(
                    obligation=obligation,
                    cart_item=allocation.cart_item,
                    vendor_event=vendor_event,
                    ledger_item=ledger_item,
                    audit_context=audit_context,
                )

        return ledger_items
