import csv
import json
import os
from typing import List, Optional

from core.models.models import (
    CourtAdjustment,
    Obligation,
    ObligationActivityLog,
    ObligationCreationRequest,
    ObligationEventType,
    ObligationFilterRequest,
    ObligationLabel,
    ObligationProcessingResult,
    ObligationStatus,
    PayableIdentifiers,
    RawAllocation,
    Transaction,
    VendorEvent,
    VendorEventProcessingStatus,
    VendorEventType,
    VendorName,
)
from processors.cart_processor import CartProcessor
from processors.transaction_processor import TransactionProcessor


class VendorEventStore:
    vendor_event_csv_path = "/Users/obvio/Desktop/gringotts/data/vendor_event.csv"

    @staticmethod
    def update_vendor_event(updated_vendor_event: VendorEvent):
        """Update an existing obligation in the CSV."""
        vendor_events = VendorEventStore.read_vendor_events()
        for i in range(len(vendor_events)):
            if vendor_events[i].id == updated_vendor_event.id:
                vendor_events[i] = updated_vendor_event
                break
        with open(VendorEventStore.vendor_event_csv_path, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "id",
                    "event_type",
                    "vendor_name",
                    "allocation_list",
                    "metadata",
                    "court_adjustment",
                    "processing_status",
                    "payment_mode",
                    "transaction_id",
                    "is_settled",
                    "cart_id",
                ]
            )
            for event in vendor_events:
                writer.writerow(
                    [
                        event.id,
                        event.event_type,
                        event.vendor_name,
                        json.dumps(
                            [
                                {
                                    "owner_id": allocation.obligation_identifiers.owner_id,
                                    "owner_type": allocation.obligation_identifiers.owner_type,
                                    "label": allocation.obligation_identifiers.label.value,
                                    "amount": allocation.amount,
                                    "obligation_id": allocation.obligation_id,
                                }
                                for allocation in (event.allocation_list or [])
                            ]
                        ),
                        json.dumps(event.metadata),
                        (
                            json.dumps(event.court_adjustment.raw_allocation.__dict__)
                            if event.court_adjustment
                            else None
                        ),
                        event.processing_status,
                        event.payment_mode.value if event.payment_mode else None,
                        event.transaction.id if event.transaction else None,
                        event.is_settled if event.is_settled is not None else None,
                        event.cart.id if event.cart else None,
                    ]
                )

    @staticmethod
    def read_vendor_events() -> List[VendorEvent]:
        """Read all vendor events from the CSV file."""
        vendor_events = []
        with open(VendorEventStore.vendor_event_csv_path, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                vendor_event = VendorEvent(
                    id=int(row["id"]),
                    event_type=row["event_type"],
                    vendor_name=row["vendor_name"],
                    metadata=row["metadata"],
                    court_adjustment=row["court_adjustment"],
                    processing_status=row["processing_status"],
                    payment_mode=row["payment_mode"],
                    is_settled=(
                        row["is_settled"] == "TRUE"
                        if row["is_settled"] is not None
                        else None
                    ),
                )
                transaction_id = row["transaction_id"]
                cart_id = row["cart_id"]

                if transaction_id:
                    transaction = TransactionProcessor.get_transaction_by_id(
                        transaction_id=int(transaction_id)
                    )
                    vendor_event.transaction = transaction

                if cart_id:
                    # Assuming you have a method to get cart by ID, you can implement it similarly to transactions
                    cart = CartProcessor.get_cart_by_id(cart_id=int(cart_id))
                    vendor_event.cart = cart

                vendor_events.append(vendor_event)

        return vendor_events

    @staticmethod
    def filter_vendor_events(
        vendor_name: Optional[VendorName] = None,
        event_type: Optional[VendorEventType] = None,
        processing_status: Optional[VendorEventProcessingStatus] = None,
    ) -> List[VendorEvent]:
        """Filter vendor events by event type."""
        vendor_events = VendorEventStore.read_vendor_events()
        return [
            event
            for event in vendor_events
            if (vendor_name is None or event.vendor_name == vendor_name)
            and (event_type is None or event.event_type == event_type)
            and (
                processing_status is None
                or event.processing_status == processing_status
            )
        ]
