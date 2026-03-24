import csv
import json
import os
from typing import List

from core.models.models import (
    Cart,
    LedgerAllocation,
    LedgerAllocationItemInput,
    LedgerItem,
    LedgerStage,
    TransactionBreakdownType,
    VendorEvent,
    VendorEventType,
    VendorName,
)
from processors.cart_processor import CartProcessor
from processors.transaction_processor import TransactionProcessor


class Ledger:
    ledger_csv_path = "/Users/obvio/Desktop/gringotts/data/ledger.csv"
    _counter_file = "/Users/obvio/Desktop/gringotts/data/obligation_id_counter.txt"

    # Initialize the counter from the file or default to 1
    if os.path.exists(_counter_file):
        with open(_counter_file, "r") as file:
            _id_counter = int(file.read().strip())
    else:
        _id_counter = 1

    @staticmethod
    def _increment_counter():
        """Increment the counter and save it to the file."""
        Ledger._id_counter += 1
        with open(Ledger._counter_file, "w") as file:
            file.write(str(Ledger._id_counter))

    @staticmethod
    def store_ledger_item(ledger_item: LedgerItem):
        """Store in CSV, add column names if it's a new file."""
        file_exists = False
        try:
            with open(Ledger.ledger_csv_path, mode="r") as file:
                file_exists = True
        except FileNotFoundError:
            pass

        with open(Ledger.ledger_csv_path, mode="a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:
                # Write header row if the file is new
                writer.writerow(
                    [
                        "id",
                        "vendor_name",
                        "amount",
                        "stage",
                        "type",
                        "label",
                        "cart_id",
                        "transaction_id",
                        "confirmed_at",
                        "settled_at",
                        "allocations",
                    ]
                )
            writer.writerow(
                [
                    ledger_item.id,
                    ledger_item.vendor_name,
                    ledger_item.amount,
                    ledger_item.stage,
                    ledger_item.type,
                    ledger_item.label,
                    ledger_item.cart.id,
                    ledger_item.transaction.id if ledger_item.transaction else None,
                    ledger_item.confirmed_at,
                    ledger_item.settled_at,
                    (
                        json.dumps(
                            [
                                {
                                    "cart_item_id": allocation.cart_item.id,
                                    "obligation_id": allocation.cart_item.obligation.id,
                                    "amount": allocation.amount,
                                }
                                for allocation in ledger_item.allocations
                            ]
                        )
                        if ledger_item.allocations
                        else None
                    ),
                ]
            )

    @staticmethod
    def update_ledger_item(updated_ledger_item: LedgerItem):
        print("Updating ledger item:", updated_ledger_item)
        """Update an existing ledger item in the CSV."""
        ledger_items = Ledger.read_ledger_from_csv()
        for i in range(len(ledger_items)):
            item = ledger_items[i]
            if item.id == updated_ledger_item.id:
                ledger_items[i] = updated_ledger_item  # Update the ledger item
                break

        with open(Ledger.ledger_csv_path, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "id",
                    "vendor_name",
                    "amount",
                    "stage",
                    "type",
                    "label",
                    "cart_id",
                    "transaction_id",
                    "confirmed_at",
                    "settled_at",
                    "allocations",
                ]
            )
            for ledger_item in ledger_items:
                writer.writerow(
                    [
                        ledger_item.id,
                        ledger_item.vendor_name,
                        ledger_item.amount,
                        ledger_item.stage,
                        ledger_item.type,
                        ledger_item.label,
                        ledger_item.cart.id,
                        ledger_item.transaction.id if ledger_item.transaction else None,
                        ledger_item.confirmed_at,
                        ledger_item.settled_at,
                        (
                            json.dumps(
                                [
                                    {
                                        "cart_item_id": allocation.cart_item.id,
                                        "obligation_id": allocation.cart_item.obligation.id,
                                        "amount": allocation.amount,
                                    }
                                    for allocation in ledger_item.allocations
                                ]
                            )
                            if ledger_item.allocations
                            else None
                        ),
                    ]
                )

    @staticmethod
    def read_ledger_from_csv() -> List[LedgerItem]:
        """Read ledger items from the CSV file."""
        ledger_items = []
        try:
            with open(Ledger.ledger_csv_path, mode="r") as file:
                reader = csv.DictReader(file)
                for row in reader:

                    allocations = None
                    allocations_data = (
                        json.loads(row["allocations"]) if row["allocations"] else None
                    )
                    if allocations_data:
                        allocations = []
                        for allocation in allocations_data:
                            cart_item = CartProcessor.get_cart_item_by_id(
                                allocation["cart_item_id"]
                            )
                            allocations.append(
                                LedgerAllocation(
                                    ledger_id=int(row["id"]),
                                    cart_item=cart_item,
                                    amount=allocation["amount"],
                                )
                            )

                    ledger_items.append(
                        LedgerItem(
                            id=int(row["id"]),
                            transaction=TransactionProcessor.get_transaction_by_id(
                                int(row["transaction_id"])
                            ),
                            vendor_name=row["vendor_name"],
                            amount=float(row["amount"]),
                            stage=LedgerStage(row["stage"]),
                            type=TransactionBreakdownType(row["type"]),
                            label=row["label"],
                            cart=CartProcessor.get_cart_by_id(int(row["cart_id"])),
                            confirmed_at=(
                                int(row["confirmed_at"])
                                if row["confirmed_at"]
                                else None
                            ),
                            settled_at=(
                                int(row["settled_at"]) if row["settled_at"] else None
                            ),
                            allocations=allocations,
                        )
                    )
        except FileNotFoundError:
            pass  # If the file doesn't exist, return an empty list
        return ledger_items

    @staticmethod
    def read_ledger_allocations() -> List[LedgerAllocation]:
        """Read ledger allocations from the CSV file."""
        ledger_allocations = []
        try:
            with open(Ledger.ledger_csv_path, mode="r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    allocations_data = (
                        json.loads(row["allocations"]) if row["allocations"] else None
                    )
                    if allocations_data:
                        for allocation in allocations_data:
                            cart_item = CartProcessor.get_cart_item_by_id(
                                allocation["cart_item_id"]
                            )
                            ledger_allocations.append(
                                LedgerAllocation(
                                    ledger_id=int(row["id"]),
                                    cart_item=cart_item,
                                    amount=allocation["amount"],
                                )
                            )
        except FileNotFoundError:
            pass  # If the file doesn't exist, return an empty list
        return ledger_allocations

    @staticmethod
    def get_corresponding_ledger_stage(
        vendor_event_type: VendorEventType,
    ) -> LedgerStage:
        mapping = {
            VendorEventType.PAYMENT_CONFIRMED: LedgerStage.PAYMENT_CONFIRMED,
            VendorEventType.PAYMENT_SETTLED: LedgerStage.PAYMENT_SETTLED,
            VendorEventType.PAYMENT_REFUNDED: LedgerStage.PAYMENT_REFUNDED,
            VendorEventType.PAYMENT_DISPUTE_FUNDS_WITHDRAWN: LedgerStage.PAYMENT_DISPUTE_FUNDS_WITHDRAWN,
            VendorEventType.PAYMENT_DISPUTE_FUNDS_RETURNED: LedgerStage.PAYMENT_DISPUTE_FUNDS_RETURNED,
        }
        return mapping.get(vendor_event_type)

    @staticmethod
    def record_event(
        vendor_event: VendorEvent,
        item_allocations: List[LedgerAllocationItemInput],
        cart: Cart,
        record_time: int,
    ) -> List[LedgerItem]:

        transaction = vendor_event.transaction
        assert (
            transaction is not None
        ), "Transaction must be present in the vendor event in ledger recording"

        transaction_breakdown = transaction.payment_breakdown
        ledger_itens_list = []
        for breakdown_item in transaction_breakdown:

            existing_ledger_item = (
                Ledger.identify_existing_ledger_record_for_payment_confirmation(
                    vendor_name=vendor_event.vendor_name,
                    transaction_id=transaction.id,
                    type=breakdown_item.type,
                    label=breakdown_item.label,
                    cart_id=cart.id,
                )
            )
            if (
                existing_ledger_item
                and existing_ledger_item.stage == LedgerStage.PAYMENT_SETTLED
            ):
                ledger_itens_list.append(existing_ledger_item)
                continue

            if (
                existing_ledger_item
                and existing_ledger_item.stage == LedgerStage.PAYMENT_CONFIRMED
                and vendor_event.event_type == VendorEventType.PAYMENT_SETTLED
            ):
                existing_ledger_item.stage = LedgerStage.PAYMENT_SETTLED
                existing_ledger_item.settled_at = record_time
                Ledger.update_ledger_item(existing_ledger_item)
                ledger_itens_list.append(existing_ledger_item)
                continue

            ledger_event_type = Ledger.get_corresponding_ledger_stage(
                vendor_event.event_type
            )

            allocations = None

            ledger_item = LedgerItem(
                id=Ledger._id_counter,
                cart=cart,
                vendor_name=vendor_event.vendor_name,
                amount=breakdown_item.amount,
                stage=Ledger.get_corresponding_ledger_stage(vendor_event.event_type),
                type=breakdown_item.type,
                label=breakdown_item.label,
                transaction=transaction,
                confirmed_at=(
                    record_time
                    if ledger_event_type == LedgerStage.PAYMENT_CONFIRMED
                    or vendor_event.is_settled
                    else None
                ),
                settled_at=(record_time if vendor_event.is_settled else None),
            )
            if breakdown_item.type == TransactionBreakdownType.PAYMENT:
                allocations = [
                    LedgerAllocation(
                        ledger_id=Ledger._id_counter,
                        cart_item=allocation.cart_item,
                        amount=allocation.amount,
                    )
                    for allocation in item_allocations
                ]
            ledger_item.allocations = allocations
            Ledger._increment_counter()
            Ledger.store_ledger_item(ledger_item)

            ledger_itens_list.append(ledger_item)
        return ledger_itens_list

    @staticmethod
    def identify_existing_ledger_record_for_payment_confirmation(
        vendor_name: VendorName,
        transaction_id: int,
        type: TransactionBreakdownType,
        label: str,
        cart_id: int,
    ) -> LedgerItem:
        ledger_items = Ledger.read_ledger_from_csv()
        for item in ledger_items:
            if (
                item.cart.id == cart_id
                and item.vendor_name == vendor_name
                and item.type == type
                and item.label == label
                and item.transaction.id == transaction_id
                and item.stage
                in [LedgerStage.PAYMENT_CONFIRMED, LedgerStage.PAYMENT_SETTLED]
            ):
                print("Found existing ledger item for payment confirmation:", item)
                return item
