import copy
import csv
import json
import os
from dataclasses import dataclass
from typing import List, Optional

from core.models.models import (
    Refund,
    RefundItemAllocation,
    RefundProcessingStatus,
    VendorName,
)
from processors.cart_processor import CartProcessor
from processors.transaction_processor import TransactionProcessor


class RefundProcessor:
    refund_csv_path = "/Users/obvio/Desktop/gringotts/data/refunds.csv"

    @staticmethod
    def read() -> List[Refund]:
        """Read refund requests from the CSV file."""
        refunds = []
        try:
            with open(RefundProcessor.refund_csv_path, mode="r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    cart_id = int(row["cart_id"])
                    cart = CartProcessor.get_cart_by_id(cart_id)
                    refund_item_allocation_data = json.loads(
                        row["refund_item_allocations"]
                    )
                    refund_item_allocations = []
                    for item in refund_item_allocation_data:
                        cart_item = CartProcessor.get_cart_item_by_id(
                            int(item["cart_item_id"])
                        )
                        refund_item_allocations.append(
                            RefundItemAllocation(
                                cart_item=cart_item,
                                amount=item["amount"],
                            )
                        )

                    transaction = TransactionProcessor.get_transaction_by_id(
                        int(row["transaction_id"])
                    )
                    metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                    refunds.append(
                        Refund(
                            cart=cart,
                            refund_amount=int(row["refund_amount"]),
                            transaction=transaction,
                            refund_item_allocations=refund_item_allocations,
                            vendor_name=VendorName(row["vendor_name"]),
                            processing_status=RefundProcessingStatus(
                                row["processing_status"]
                            ),
                            metadata=metadata,
                        )
                    )
        except FileNotFoundError:
            pass
        # If the file doesn't exist, return an empty list
        return refunds

    @staticmethod
    def filter(
        vendor_name: Optional[VendorName] = None,
        processing_status: Optional[RefundProcessingStatus] = None,
    ) -> List[Refund]:
        """Filter vendor events by event type."""
        refunds = RefundProcessor.read()
        return [
            event
            for event in refunds
            if (vendor_name is None or event.vendor_name == vendor_name)
            and (
                processing_status is None
                or event.processing_status == processing_status
            )
        ]
