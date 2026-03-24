import csv
import json
import os
from typing import List

from core.models.models import (
    CourtAdjustment,
    Obligation,
    ObligationActivityLog,
    ObligationCreationRequest,
    ObligationEventType,
    ObligationFilterRequest,
    ObligationProcessingResult,
    ObligationStatus,
    RawAllocation,
    Transaction,
    TransactionAllocationType,
    TransactionBreakdownItem,
    TransactionBreakdownItemType,
    TransactionItemAllocation,
    VendorEvent,
)


class TransactionProcessor:
    transaction_csv_path = "/Users/obvio/Desktop/gringotts/data/transactions.csv"

    @staticmethod
    def read_transactions() -> List[Transaction]:
        """Read all transactions from the CSV file."""
        transactions = []
        with open(TransactionProcessor.transaction_csv_path, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                payment_breakdown_list = json.loads(row["payment_breakdown"])
                transaction_breakdown_item_list = []
                for item in payment_breakdown_list:
                    transaction_breakdown_item_list.append(
                        TransactionBreakdownItem(
                            type=TransactionBreakdownItemType(item["type"]),
                            amount=item["amount"],
                            label=item.get("label"),
                        )
                    )
                item_allocations = json.loads(row["item_allocations"])
                item_allocations_list = []
                for item in item_allocations:
                    item_allocations_list.append(
                        TransactionItemAllocation(
                            allocation_type=TransactionAllocationType(
                                item["allocation_type"]
                            ),
                            amount=item["amount"],
                            owner_id=item.get("owner_id"),
                            owner_type=item.get("owner_type"),
                            label=item.get("label"),
                            cart_item_id=item.get("cart_item_id"),
                        )
                    )
                transactions.append(
                    Transaction(
                        id=int(row["id"]),
                        vendor_name=row["vendor_name"],
                        vendor_reference_id=row["vendor_reference_id"],
                        vendor_reference_type=row["vendor_reference_type"],
                        amount=int(row["amount"]),
                        payment_breakdown=transaction_breakdown_item_list,
                        item_allocations=item_allocations_list,
                    )
                )
        return transactions

    @staticmethod
    def get_transaction_by_id(transaction_id: int) -> Transaction:
        """Get a transaction by its ID."""
        transactions = TransactionProcessor.read_transactions()
        for transaction in transactions:
            if transaction.id == transaction_id:
                return transaction
        raise ValueError(f"Transaction with ID {transaction_id} not found.")
