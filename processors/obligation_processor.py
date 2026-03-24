import copy
import csv
import os
from dataclasses import dataclass
from typing import List, Optional

from core.models.models import (
    CartItem,
    CourtAdjustment,
    LedgerItem,
    Obligation,
    ObligationActivityLog,
    ObligationCreationRequest,
    ObligationEventType,
    ObligationFilterRequest,
    ObligationLabel,
    ObligationProcessingResult,
    ObligationStatus,
    PaymentMode,
    RawAllocation,
    Transaction,
    VendorEvent,
    VendorEventType,
)


class ObligationProcessor:
    obligations_csv_path = "/Users/obvio/Desktop/gringotts/data/obligations.csv"
    obligation_activity_log_csv_path = (
        "/Users/obvio/Desktop/gringotts/data/obligation_activity_log.csv"
    )
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
        ObligationProcessor._id_counter += 1
        with open(ObligationProcessor._counter_file, "w") as file:
            file.write(str(ObligationProcessor._id_counter))

    @staticmethod
    def read_obligations_from_csv() -> List[Obligation]:
        """Read obligations from the CSV file."""
        obligations = []
        try:
            with open(ObligationProcessor.obligations_csv_path, mode="r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    obligations.append(
                        Obligation(
                            id=int(row["id"]),
                            owner_id=row["owner_id"],
                            owner_type=row["owner_type"],
                            fee_type=row["fee_type"],
                            label=row["label"],
                            status=row["status"],
                            amount=int(row["amount"]),
                            allocated_total=int(row.get("allocated_total", 0)),
                            outstanding_amount=int(row.get("outstanding_amount", 0)),
                            overpaid_amount=int(row.get("overpaid_amount", 0)),
                            waived_amount=int(row.get("waived_amount", 0)),
                            locked_by=row["locked_by"],
                        )
                    )
        except FileNotFoundError:
            pass  # If the file doesn't exist, return an empty list
        return obligations

    @staticmethod
    def get_obligation_by_id(obligation_id: int) -> Obligation:
        """Get an obligation by its ID."""
        obligations = ObligationProcessor.read_obligations_from_csv()
        for obligation in obligations:
            if obligation.id == obligation_id:
                return obligation
        return None

    @staticmethod
    def process(court_adjustment: CourtAdjustment) -> ObligationProcessingResult:
        """Process a court adjustment and return an obligation processing result."""
        # Placeholder logic for processing
        obligation = court_adjustment.raw_allocation.owner_id  # Example
        return ObligationProcessingResult(
            obligation=obligation,
            citation=None,  # Replace with actual citation logic
            obligation_activity_log=None,  # Replace with actual activity log logic
        )

    @staticmethod
    def authorise(
        obligations: List[Obligation], transaction: Transaction
    ) -> List[Obligation]:
        """Authorise a list of obligations with a transaction."""
        for obligation in obligations:
            obligation.status = "authorised"  # Replace with actual status enum
        return obligations

    @staticmethod
    def settle(
        obligations: List[Obligation], transaction: Transaction
    ) -> List[Obligation]:
        """Settle a list of obligations with a transaction."""
        for obligation in obligations:
            obligation.status = "settled"  # Replace with actual status enum
        return obligations

    @staticmethod
    def get_from_raw(raw_allocations: List[RawAllocation]) -> List[Obligation]:
        """Convert raw allocations to obligations."""
        obligations = []
        for raw_allocation in raw_allocations:
            obligations.append(
                Obligation(
                    owner_id=raw_allocation.owner_id,
                    owner_type=raw_allocation.owner_type,
                    fee_type=raw_allocation.fee_type,
                    name="Generated Obligation",  # Replace with actual logic
                    status="pending",  # Replace with actual status enum
                    locked_by=None,
                )
            )
        return obligations

    @staticmethod
    def store_obligations_activity_log(obligation_activity_log: ObligationActivityLog):
        """Store in csv"""
        file_exists = False
        try:
            with open(
                ObligationProcessor.obligation_activity_log_csv_path, mode="r"
            ) as file:
                file_exists = True
        except FileNotFoundError:
            pass

        with open(
            ObligationProcessor.obligation_activity_log_csv_path,
            mode="a",
            newline="",
        ) as file:
            writer = csv.writer(file)
            if not file_exists:
                # Write header row if the file is new
                writer.writerow(
                    [
                        "obligation_id",
                        "old_status",
                        "new_status",
                        "event_type",
                        "ledger_item_id",
                        "vendor_event_id",
                        "transaction_id",
                        "cart_item_id",
                        "locked_by",
                        "allocated_total",
                        "outstanding_amount",
                        "overpaid_amount",
                        "waived_amount",
                        "allocated_delta",
                        "status_updated",
                    ]
                )

            writer.writerow(
                [
                    obligation_activity_log.obligation_id,
                    obligation_activity_log.old_status,
                    obligation_activity_log.new_status,
                    obligation_activity_log.event_type,
                    obligation_activity_log.ledger_item_id,
                    obligation_activity_log.vendor_event_id,
                    obligation_activity_log.transaction_id,
                    obligation_activity_log.cart_item_id,
                    obligation_activity_log.locked_by,
                    obligation_activity_log.allocated_total,
                    obligation_activity_log.outstanding_amount,
                    obligation_activity_log.overpaid_amount,
                    obligation_activity_log.waived_amount,
                    obligation_activity_log.allocated_delta,
                    obligation_activity_log.status_updated,
                ]
            )

    @staticmethod
    def store_obligation(obligation: Obligation):
        """Store in CSV, add column names if it's a new file."""
        file_exists = False
        try:
            with open(ObligationProcessor.obligations_csv_path, mode="r") as file:
                file_exists = True
        except FileNotFoundError:
            pass

        with open(
            ObligationProcessor.obligations_csv_path, mode="a", newline=""
        ) as file:
            writer = csv.writer(file)
            if not file_exists:
                # Write header row if the file is new
                writer.writerow(
                    [
                        "id",
                        "owner_id",
                        "owner_type",
                        "fee_type",
                        "label",
                        "status",
                        "amount",
                        "allocated_total",
                        "outstanding_amount",
                        "overpaid_amount",
                        "waived_amount",
                        "locked_by",
                    ]
                )
            writer.writerow(
                [
                    obligation.id,
                    obligation.owner_id,
                    obligation.owner_type,
                    obligation.fee_type,
                    obligation.label,
                    obligation.status,
                    obligation.amount,
                    obligation.allocated_total,
                    obligation.outstanding_amount,
                    obligation.overpaid_amount,
                    obligation.waived_amount,
                    obligation.locked_by,
                ]
            )

    @staticmethod
    def update_obligation(updated_obligation: Obligation):
        """Update an existing obligation in the CSV."""
        obligations = []
        with open(ObligationProcessor.obligations_csv_path, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if int(row["id"]) == updated_obligation.id:
                    obligations.append(updated_obligation)  # Update the obligation
                else:
                    obligations.append(
                        Obligation(
                            id=int(row["id"]),
                            owner_id=row["owner_id"],
                            owner_type=row["owner_type"],
                            fee_type=row["fee_type"],
                            label=row["label"],
                            status=row["status"],
                            amount=int(row["amount"]),
                            allocated_total=int(row.get("allocated_total", 0)),
                            outstanding_amount=int(row.get("outstanding_amount", 0)),
                            overpaid_amount=int(row.get("overpaid_amount", 0)),
                            waived_amount=int(row.get("waived_amount", 0)),
                            locked_by=row["locked_by"],
                        )
                    )
        with open(
            ObligationProcessor.obligations_csv_path, mode="w", newline=""
        ) as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "id",
                    "owner_id",
                    "owner_type",
                    "fee_type",
                    "label",
                    "status",
                    "amount",
                    "allocated_total",
                    "outstanding_amount",
                    "overpaid_amount",
                    "waived_amount",
                    "locked_by",
                ]
            )
            for obligation in obligations:
                writer.writerow(
                    [
                        obligation.id,
                        obligation.owner_id,
                        obligation.owner_type,
                        obligation.fee_type,
                        obligation.label,
                        obligation.status,
                        obligation.amount,
                        obligation.allocated_total,
                        obligation.outstanding_amount,
                        obligation.overpaid_amount,
                        obligation.waived_amount,
                        obligation.locked_by,
                    ]
                )

    @staticmethod
    def invalid_obligation_statuses():
        """Return a set of invalid obligation statuses."""
        return [
            ObligationStatus.SUPERSEDED,
            ObligationStatus.VOIDED,
            ObligationStatus.WAIVED,
        ]

    @staticmethod
    def add_payable(request: ObligationCreationRequest) -> Obligation:
        """Add a payable obligation based on a creation request."""
        existing_obligation = ObligationProcessor.get_valid_obligation_against_payable(
            owner_id=request.owner_id,
            owner_type=request.owner_type,
            label=request.label,
        )
        if existing_obligation:
            return existing_obligation

        obligation_id = ObligationProcessor._id_counter
        ObligationProcessor._increment_counter()
        obligation = Obligation(
            id=obligation_id,
            amount=request.amount,
            allocated_total=0,
            outstanding_amount=request.amount,
            overpaid_amount=0,
            owner_id=request.owner_id,
            owner_type=request.owner_type,
            fee_type=request.type,
            label=request.label,
            status=request.status,
            locked_by=None,
        )
        ObligationProcessor.store_obligation(obligation)
        obligation_activity_log = ObligationActivityLog(
            old_status=None,
            status_updated=False,
            new_status=obligation.status,
            obligation_id=obligation.id,
            event_type=ObligationEventType.DEBT_CREATED,
            allocated_total=obligation.allocated_total,
            outstanding_amount=obligation.outstanding_amount,
            overpaid_amount=obligation.overpaid_amount,
            waived_amount=obligation.waived_amount,
            allocated_delta=0,
        )
        ObligationProcessor.store_obligations_activity_log(obligation_activity_log)
        return obligation

    @staticmethod
    def filter_obligations(
        obligations: List[Obligation], filter_request: ObligationFilterRequest
    ) -> List[Obligation]:

        filtered_obligations = [
            obligation
            for obligation in obligations
            if (
                filter_request.owner_id is None
                or obligation.owner_id == filter_request.owner_id
            )
            and (
                filter_request.owner_type is None
                or obligation.owner_type == filter_request.owner_type
            )
            and (
                filter_request.fee_type is None
                or obligation.fee_type == filter_request.fee_type
            )
            and (
                filter_request.status is None
                or obligation.status == filter_request.status
            )
        ]
        return filtered_obligations

    @staticmethod
    def lock_obligations(
        cart_items: List[CartItem], lock_by: int, payment_mode: PaymentMode
    ) -> List[Obligation]:
        """Lock a list of obligations."""

        is_locking_allowed = all(
            cart_item.obligation.status == ObligationStatus.OPEN
            for cart_item in cart_items
        )
        if not is_locking_allowed:
            raise ValueError("All obligations must be open to be locked.")

        for cart_item in cart_items:
            obligation = cart_item.obligation
            old_status = obligation.status
            obligation.status = ObligationStatus.LOCKED
            obligation.locked_by = lock_by
            obligation_activity_log = ObligationActivityLog(
                obligation_id=obligation.id,
                old_status=old_status,
                new_status=obligation.status,
                event_type=ObligationEventType.LOCKED,
                locked_by=lock_by,
                allocated_total=obligation.allocated_total,
                outstanding_amount=obligation.outstanding_amount,
                overpaid_amount=obligation.overpaid_amount,
                waived_amount=obligation.waived_amount,
                allocated_delta=0,
                status_updated=True,
                cart_item_id=cart_item.id,
                payment_mode=payment_mode,
            )
            ObligationProcessor.store_obligations_activity_log(obligation_activity_log)
            ObligationProcessor.update_obligation(obligation)

    @staticmethod
    def get_valid_obligation_against_payable(
        owner_id: str, owner_type: str, label: ObligationLabel
    ) -> Obligation:
        obligations = ObligationProcessor.read_obligations_from_csv()
        for obligation in obligations:
            if (
                obligation.status
                not in [
                    ObligationStatus.SUPERSEDED,
                    ObligationStatus.VOIDED,
                    ObligationStatus.WAIVED,
                ]
                and obligation.owner_id == owner_id
                and obligation.owner_type == owner_type
                and obligation.label == label
            ):
                return obligation

    @staticmethod
    def update_obligation_according_to_ledger(
        obligation: Obligation,
        cart_item: CartItem,
        vendor_event: VendorEvent,
        ledger_item: LedgerItem,
    ) -> Obligation:
        """Update the payment details of an obligation."""
        old_obligation = copy.deepcopy(obligation)
        print("old_obligation:", old_obligation)
        allocated_total, outstanding_amount, overpaid_amount = (
            ObligationProcessor.get_obligation_payment_summary(obligation)
        )

        obligation.allocated_total = allocated_total
        obligation.outstanding_amount = outstanding_amount
        obligation.overpaid_amount = overpaid_amount

        # Only move to CLOSED if this obligation is still collectible/resolvable
        if (
            obligation.outstanding_amount == 0
            and obligation.status
            not in ObligationProcessor.invalid_obligation_statuses()
        ):
            obligation.status = ObligationStatus.CLOSED
            obligation.locked_by = None
        elif (
            obligation.status not in ObligationProcessor.invalid_obligation_statuses()
            and outstanding_amount > 0
        ):
            obligation.status = ObligationStatus.OPEN
            obligation.locked_by = None
        elif (
            obligation.status == ObligationStatus.LOCKED
            and obligation.locked_by == cart_item.cart_id
        ):
            obligation.status = ObligationStatus.OPEN
            obligation.locked_by = None

        ObligationProcessor.update_obligation(obligation)

        is_status_changed = old_obligation.status != obligation.status
        allocated_delta = obligation.allocated_total - old_obligation.allocated_total

        if vendor_event.event_type == VendorEventType.PAYMENT_CONFIRMED:
            obligation_activity_status = ObligationEventType.PAYMENT_AUTHORISED
        elif vendor_event.event_type == VendorEventType.PAYMENT_SETTLED:
            obligation_activity_status = ObligationEventType.PAYMENT_SETTLED
        elif vendor_event.event_type == VendorEventType.PAYMENT_REFUNDED:
            obligation_activity_status = ObligationEventType.PAYMENT_REFUNDED
        elif vendor_event.event_type == VendorEventType.PAYMENT_DISPUTE_FUNDS_WITHDRAWN:
            obligation_activity_status = (
                ObligationEventType.PAYMENT_DISPUTE_FUNDS_WITHDRAWN
            )
        elif vendor_event.event_type == VendorEventType.PAYMENT_DISPUTE_FUNDS_RETURNED:
            obligation_activity_status = (
                ObligationEventType.PAYMENT_DISPUTE_FUNDS_RETURN
            )
        else:
            obligation_activity_status = ObligationEventType.GENERAL_UPDATE

        obligation_activity_log = ObligationActivityLog(
            obligation_id=obligation.id,
            old_status=old_obligation.status,
            new_status=obligation.status,
            status_updated=is_status_changed,
            allocated_total=obligation.allocated_total,
            outstanding_amount=obligation.outstanding_amount,
            overpaid_amount=obligation.overpaid_amount,
            waived_amount=obligation.waived_amount,
            allocated_delta=allocated_delta,
            event_type=obligation_activity_status,
            ledger_item_id=ledger_item.id,
            vendor_event_id=vendor_event.id,
            transaction_id=(
                ledger_item.transaction.id if ledger_item.transaction else None
            ),
            cart_item_id=cart_item.id,
            locked_by=obligation.locked_by,
            payment_mode=vendor_event.payment_mode,
        )
        ObligationProcessor.store_obligations_activity_log(obligation_activity_log)

        return obligation

    @staticmethod
    def get_obligation_payment_summary(obligation: Obligation):
        from processors.ledger import Ledger

        ledger_allocations = Ledger.read_ledger_allocations()

        allocated_total = 0

        for allocation in ledger_allocations:
            if allocation.cart_item.obligation.id == obligation.id:
                allocated_total += allocation.amount

        outstanding_amount = max(obligation.amount - allocated_total, 0)
        overpaid_amount = max(allocated_total - obligation.amount, 0)
        return allocated_total, outstanding_amount, overpaid_amount

    @staticmethod
    def waive_partially_paid_obligation(
        obligation: Obligation,
    ) -> Obligation:
        """
        Waive the remaining outstanding amount on a partially paid obligation.

        Rule:
        - if obligation already has some allocated amount, final status = CLOSED
        - if no allocated amount exists, use void_obligation instead
        """
        if obligation.outstanding_amount <= 0:
            raise ValueError("Outstanding amount must be greater than zero to waive.")

        if obligation.allocated_total <= 0:
            raise ValueError(
                "waive_partially_paid_obligation can only be used for partially paid obligations."
            )

        old_status = obligation.status
        waive_amount = obligation.outstanding_amount

        obligation.waived_amount += waive_amount
        obligation.outstanding_amount = 0
        obligation.overpaid_amount = max(
            obligation.allocated_total + obligation.waived_amount - obligation.amount,
            0,
        )
        obligation.status = ObligationStatus.CLOSED
        obligation.locked_by = None
        ObligationProcessor.update_obligation(obligation)

        activity_log = ObligationActivityLog(
            obligation_id=obligation.id,
            old_status=old_status,
            new_status=obligation.status,
            event_type=ObligationEventType.PARTIAL_WAIVE,
            ledger_item_id=None,
            vendor_event_id=None,
            transaction_id=None,
            cart_item_id=None,
            locked_by=obligation.locked_by,
            allocated_total=obligation.allocated_total,
            outstanding_amount=obligation.outstanding_amount,
            overpaid_amount=obligation.overpaid_amount,
            waived_amount=obligation.waived_amount,
            allocated_delta=0,
            status_updated=old_status != obligation.status,
        )
        ObligationProcessor.store_obligations_activity_log(activity_log)

        return obligation

    @staticmethod
    def waive_obligation(
        obligation: Obligation,
    ) -> Obligation:
        """
        waive a completely unpaid obligation.

        Rule:
        - if obligation is fully unpaid, final status = WAIVED
        - if obligation has any payment allocated, use waive_partially_paid_obligation instead
        """
        if obligation.outstanding_amount <= 0:
            raise ValueError("Obligation has no outstanding amount to waive.")

        if obligation.allocated_total > 0:
            raise ValueError(
                "void_obligation can only be used for fully unpaid obligations."
            )

        old_status = obligation.status
        waive_amount = obligation.outstanding_amount

        obligation.waived_amount += waive_amount
        obligation.outstanding_amount = 0
        obligation.overpaid_amount = max(
            obligation.allocated_total + obligation.waived_amount - obligation.amount,
            0,
        )
        obligation.status = ObligationStatus.WAIVED
        obligation.locked_by = None

        activity_log = ObligationActivityLog(
            obligation_id=obligation.id,
            old_status=old_status,
            new_status=obligation.status,
            event_type=ObligationEventType.WAIVED,
            ledger_item_id=None,
            vendor_event_id=None,
            transaction_id=None,
            cart_item_id=None,
            locked_by=obligation.locked_by,
            allocated_total=obligation.allocated_total,
            outstanding_amount=obligation.outstanding_amount,
            overpaid_amount=obligation.overpaid_amount,
            waived_amount=obligation.waived_amount,
            allocated_delta=0,
            status_updated=(old_status != obligation.status),
        )
        ObligationProcessor.store_obligations_activity_log(activity_log)
        ObligationProcessor.update_obligation(obligation)

        return obligation, activity_log

    @staticmethod
    def supersede_obligation(
        obligation: Obligation,
        new_amount: int,
    ) -> tuple[Obligation, Obligation, list[ObligationActivityLog]]:
        """
        Supersede an obligation by marking the old one as SUPERSEDED
        and creating a replacement obligation.

        Rules:
        - old obligation becomes non-payable
        - replacement obligation is created with the new amount
        - old financial history is preserved
        - new obligation starts fresh

        Returns:
            (old_obligation, new_obligation, activity_logs)
        """
        if new_amount < 0:
            raise ValueError("new_amount cannot be negative.")

        if (
            obligation.outstanding_amount < obligation.amount
            or obligation.status != ObligationStatus.OPEN
        ):
            raise ValueError(
                "Only open obligations with no payments allocated can be superseded."
            )

        # Mark old obligation as superseded
        obligation.locked_by = None

        # Usually superseded obligations should not remain collectible.
        # Keep historical allocated_total / waived_amount / overpaid_amount unchanged,
        # but zero out current collectable remainder.
        obligation.outstanding_amount = 0
        obligation.status = ObligationStatus.SUPERSEDED

        old_obligation_log = ObligationActivityLog(
            obligation_id=obligation.id,
            old_status=obligation.status,
            new_status=obligation.status,
            event_type=ObligationEventType.SUPERSEDED,
            ledger_item_id=None,
            vendor_event_id=None,
            transaction_id=None,
            cart_item_id=None,
            locked_by=None,
            allocated_total=obligation.allocated_total,
            outstanding_amount=obligation.outstanding_amount,
            overpaid_amount=obligation.overpaid_amount,
            waived_amount=obligation.waived_amount,
            allocated_delta=0,
            status_updated=False,
        )

        ObligationProcessor.update_obligation(obligation)
        ObligationProcessor.store_obligations_activity_log(old_obligation_log)
        new_obligation = ObligationProcessor.add_payable(
            ObligationCreationRequest(
                type=obligation.fee_type,
                amount=new_amount,
                owner_type=obligation.owner_type,
                owner_id=obligation.owner_id,
                status=ObligationStatus.OPEN,
                label=obligation.label,
            )
        )

        return new_obligation

    @staticmethod
    def get_owner_payment_summary(owner_id: str, owner_type: str):
        obligations = ObligationProcessor.read_obligations_from_csv()
        total_allocated = 0
        total_outstanding = 0
        total_overpaid = 0
        total_waived = 0
        total_amount = 0
        obligation_statuses = []
        summarised_obligation_status = ObligationStatus.OPEN

        for obligation in obligations:
            if (
                obligation.owner_id == owner_id
                and obligation.owner_type == owner_type
                and obligation.status
                not in ObligationProcessor.invalid_obligation_statuses()
            ):
                total_amount += obligation.amount
                total_allocated += obligation.allocated_total
                total_outstanding += obligation.outstanding_amount
                total_overpaid += obligation.overpaid_amount
                total_waived += obligation.waived_amount
                obligation_statuses.append(obligation.status)
        if all(status == ObligationStatus.CLOSED for status in obligation_statuses):
            summarised_obligation_status = ObligationStatus.CLOSED
        elif ObligationStatus.DISPUTED in obligation_statuses:
            summarised_obligation_status = ObligationStatus.DISPUTED
        elif any(status == ObligationStatus.OPEN for status in obligation_statuses):
            summarised_obligation_status = ObligationStatus.OPEN
        return {
            "total_amount": total_amount,
            "total_allocated": total_allocated,
            "total_outstanding": total_outstanding,
            "total_overpaid": total_overpaid,
            "total_waived": total_waived,
            "summarised_obligation_status": summarised_obligation_status,
        }
