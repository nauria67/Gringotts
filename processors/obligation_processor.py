import copy
import csv
import os
from typing import Any, List, Optional

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
from processors.log_manager import AuditLogManager


class ObligationProcessor:
    obligations_csv_path = "/Users/obvio/Desktop/gringotts/data/obligations.csv"
    obligation_activity_log_csv_path = (
        "/Users/obvio/Desktop/gringotts/data/obligation_activity_log.csv"
    )
    _counter_file = "/Users/obvio/Desktop/gringotts/data/obligation_id_counter.txt"

    if os.path.exists(_counter_file):
        with open(_counter_file, "r") as file:
            _id_counter = int(file.read().strip())
    else:
        _id_counter = 1

    @staticmethod
    def _increment_counter():
        ObligationProcessor._id_counter += 1
        with open(ObligationProcessor._counter_file, "w") as file:
            file.write(str(ObligationProcessor._id_counter))

    @staticmethod
    def _get_ctx_value(
        audit_context: Optional[dict[str, Any]], key: str
    ) -> Optional[str]:
        if not audit_context:
            return None
        value = audit_context.get(key)
        return str(value) if value is not None else None

    @staticmethod
    def _obligation_snapshot(obligation: Obligation) -> dict[str, Any]:
        return {
            "id": obligation.id,
            "owner_id": obligation.owner_id,
            "owner_type": (
                str(obligation.owner_type)
                if obligation.owner_type is not None
                else None
            ),
            "fee_type": (
                str(obligation.fee_type) if obligation.fee_type is not None else None
            ),
            "label": str(obligation.label) if obligation.label is not None else None,
            "status": str(obligation.status) if obligation.status is not None else None,
            "amount": obligation.amount,
            "allocated_total": obligation.allocated_total,
            "outstanding_amount": obligation.outstanding_amount,
            "overpaid_amount": obligation.overpaid_amount,
            "waived_amount": obligation.waived_amount,
            "locked_by": obligation.locked_by,
        }

    @staticmethod
    def _log_obligation_audit(
        *,
        action: str,
        obligation: Obligation,
        old_status: Optional[str],
        new_status: Optional[str],
        amount: Optional[int],
        before_snapshot: Optional[dict[str, Any]],
        after_snapshot: Optional[dict[str, Any]],
        audit_context: Optional[dict[str, Any]] = None,
        ledger_item_id: Optional[int] = None,
        vendor_event_id: Optional[int] = None,
        transaction_id: Optional[int] = None,
        cart_item_id: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        status: str = "success",
        reason: Optional[str] = None,
    ) -> None:
        AuditLogManager.log_event(
            domain="obligation",
            action=action,
            entity_type="obligation",
            entity_id=str(obligation.id),
            actor_type=ObligationProcessor._get_ctx_value(audit_context, "actor_type")
            or "system",
            actor_id=ObligationProcessor._get_ctx_value(audit_context, "actor_id"),
            source=ObligationProcessor._get_ctx_value(audit_context, "source")
            or "obligation_processor",
            request_id=ObligationProcessor._get_ctx_value(audit_context, "request_id"),
            correlation_id=ObligationProcessor._get_ctx_value(
                audit_context, "correlation_id"
            ),
            causation_id=ObligationProcessor._get_ctx_value(
                audit_context, "causation_id"
            ),
            obligation_id=obligation.id,
            transaction_id=transaction_id,
            vendor_event_id=vendor_event_id,
            cart_item_id=cart_item_id,
            old_status=str(old_status) if old_status is not None else None,
            new_status=str(new_status) if new_status is not None else None,
            amount=amount,
            status=status,
            reason=reason,
            before_snapshot=before_snapshot or {},
            after_snapshot=after_snapshot or {},
            metadata={
                "ledger_item_id": ledger_item_id,
                **(metadata or {}),
            },
        )

    @staticmethod
    def read_obligations_from_csv() -> List[Obligation]:
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
            pass
        return obligations

    @staticmethod
    def get_obligation_by_id(obligation_id: int) -> Optional[Obligation]:
        obligations = ObligationProcessor.read_obligations_from_csv()
        for obligation in obligations:
            if obligation.id == obligation_id:
                return obligation
        return None

    @staticmethod
    def process(court_adjustment: CourtAdjustment) -> ObligationProcessingResult:
        obligation = court_adjustment.raw_allocation.owner_id
        return ObligationProcessingResult(
            obligation=obligation,
            citation=None,
            obligation_activity_log=None,
        )

    @staticmethod
    def authorise(
        obligations: List[Obligation], transaction: Transaction
    ) -> List[Obligation]:
        for obligation in obligations:
            obligation.status = "authorised"
        return obligations

    @staticmethod
    def settle(
        obligations: List[Obligation], transaction: Transaction
    ) -> List[Obligation]:
        for obligation in obligations:
            obligation.status = "settled"
        return obligations

    @staticmethod
    def get_from_raw(raw_allocations: List[RawAllocation]) -> List[Obligation]:
        obligations = []
        for raw_allocation in raw_allocations:
            obligations.append(
                Obligation(
                    owner_id=raw_allocation.owner_id,
                    owner_type=raw_allocation.owner_type,
                    fee_type=raw_allocation.fee_type,
                    name="Generated Obligation",
                    status="pending",
                    locked_by=None,
                )
            )
        return obligations

    @staticmethod
    def store_obligations_activity_log(obligation_activity_log: ObligationActivityLog):
        file_exists = False
        try:
            with open(ObligationProcessor.obligation_activity_log_csv_path, mode="r"):
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
        file_exists = False
        try:
            with open(ObligationProcessor.obligations_csv_path, mode="r"):
                file_exists = True
        except FileNotFoundError:
            pass

        with open(
            ObligationProcessor.obligations_csv_path, mode="a", newline=""
        ) as file:
            writer = csv.writer(file)
            if not file_exists:
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
        obligations = []
        with open(ObligationProcessor.obligations_csv_path, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if int(row["id"]) == updated_obligation.id:
                    obligations.append(updated_obligation)
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
        return [
            ObligationStatus.SUPERSEDED,
            ObligationStatus.VOIDED,
            ObligationStatus.WAIVED,
        ]

    @staticmethod
    def add_payable(
        request: ObligationCreationRequest,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Obligation:
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

        ObligationProcessor._log_obligation_audit(
            action="obligation.created",
            obligation=obligation,
            old_status=None,
            new_status=obligation.status,
            amount=obligation.amount,
            before_snapshot={},
            after_snapshot=ObligationProcessor._obligation_snapshot(obligation),
            audit_context=audit_context,
            metadata={
                "event_type": str(ObligationEventType.DEBT_CREATED),
            },
        )
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
        cart_items: List[CartItem],
        lock_by: int,
        payment_mode: PaymentMode,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> List[Obligation]:
        is_locking_allowed = all(
            cart_item.obligation.status == ObligationStatus.OPEN
            for cart_item in cart_items
        )
        if not is_locking_allowed:
            raise ValueError("All obligations must be open to be locked.")

        updated_obligations = []

        for cart_item in cart_items:
            obligation = cart_item.obligation
            before_snapshot = ObligationProcessor._obligation_snapshot(obligation)
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

            ObligationProcessor._log_obligation_audit(
                action="obligation.locked",
                obligation=obligation,
                old_status=old_status,
                new_status=obligation.status,
                amount=obligation.amount,
                before_snapshot=before_snapshot,
                after_snapshot=ObligationProcessor._obligation_snapshot(obligation),
                audit_context=audit_context,
                cart_item_id=cart_item.id,
                metadata={
                    "event_type": str(ObligationEventType.LOCKED),
                    "payment_mode": str(payment_mode),
                    "locked_by": lock_by,
                },
            )
            updated_obligations.append(obligation)

        return updated_obligations

    @staticmethod
    def get_valid_obligation_against_payable(
        owner_id: str, owner_type: str, label: ObligationLabel
    ) -> Optional[Obligation]:
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
        return None

    @staticmethod
    def update_obligation_according_to_ledger(
        obligation: Obligation,
        cart_item: CartItem,
        vendor_event: VendorEvent,
        ledger_item: LedgerItem,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Obligation:
        old_obligation = copy.deepcopy(obligation)
        allocated_total, outstanding_amount, overpaid_amount = (
            ObligationProcessor.get_obligation_payment_summary(obligation)
        )

        obligation.allocated_total = allocated_total
        obligation.outstanding_amount = outstanding_amount
        obligation.overpaid_amount = overpaid_amount

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
            audit_action = "obligation.payment_confirmed"
        elif vendor_event.event_type == VendorEventType.PAYMENT_SETTLED:
            obligation_activity_status = ObligationEventType.PAYMENT_SETTLED
            audit_action = "obligation.payment_settled"
        elif vendor_event.event_type == VendorEventType.PAYMENT_REFUNDED:
            obligation_activity_status = ObligationEventType.PAYMENT_REFUNDED
            audit_action = "obligation.payment_refunded"
        elif vendor_event.event_type == VendorEventType.PAYMENT_DISPUTE_FUNDS_WITHDRAWN:
            obligation_activity_status = (
                ObligationEventType.PAYMENT_DISPUTE_FUNDS_WITHDRAWN
            )
            audit_action = "obligation.dispute_funds_withdrawn"
        elif vendor_event.event_type == VendorEventType.PAYMENT_DISPUTE_FUNDS_RETURNED:
            obligation_activity_status = (
                ObligationEventType.PAYMENT_DISPUTE_FUNDS_RETURN
            )
            audit_action = "obligation.dispute_funds_returned"
        else:
            obligation_activity_status = ObligationEventType.GENERAL_UPDATE
            audit_action = "obligation.updated"

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

        ObligationProcessor._log_obligation_audit(
            action=audit_action,
            obligation=obligation,
            old_status=old_obligation.status,
            new_status=obligation.status,
            amount=ledger_item.amount,
            before_snapshot=ObligationProcessor._obligation_snapshot(old_obligation),
            after_snapshot=ObligationProcessor._obligation_snapshot(obligation),
            audit_context=audit_context,
            ledger_item_id=ledger_item.id,
            vendor_event_id=vendor_event.id,
            transaction_id=(
                ledger_item.transaction.id if ledger_item.transaction else None
            ),
            cart_item_id=cart_item.id,
            metadata={
                "event_type": str(obligation_activity_status),
                "allocated_delta": allocated_delta,
                "payment_mode": (
                    str(vendor_event.payment_mode)
                    if vendor_event.payment_mode is not None
                    else None
                ),
            },
        )

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
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Obligation:
        if obligation.outstanding_amount <= 0:
            raise ValueError("Outstanding amount must be greater than zero to waive.")

        if obligation.allocated_total <= 0:
            raise ValueError(
                "waive_partially_paid_obligation can only be used for partially paid obligations."
            )

        before_snapshot = ObligationProcessor._obligation_snapshot(obligation)
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

        ObligationProcessor._log_obligation_audit(
            action="obligation.partial_waive_applied",
            obligation=obligation,
            old_status=old_status,
            new_status=obligation.status,
            amount=waive_amount,
            before_snapshot=before_snapshot,
            after_snapshot=ObligationProcessor._obligation_snapshot(obligation),
            audit_context=audit_context,
            metadata={
                "event_type": str(ObligationEventType.PARTIAL_WAIVE),
                "waive_amount": waive_amount,
            },
        )

        return obligation

    @staticmethod
    def waive_obligation(
        obligation: Obligation,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Obligation:
        if obligation.outstanding_amount <= 0:
            raise ValueError("Obligation has no outstanding amount to waive.")

        if obligation.allocated_total > 0:
            raise ValueError(
                "void_obligation can only be used for fully unpaid obligations."
            )

        before_snapshot = ObligationProcessor._obligation_snapshot(obligation)
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

        ObligationProcessor.update_obligation(obligation)

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

        ObligationProcessor._log_obligation_audit(
            action="obligation.waived",
            obligation=obligation,
            old_status=old_status,
            new_status=obligation.status,
            amount=waive_amount,
            before_snapshot=before_snapshot,
            after_snapshot=ObligationProcessor._obligation_snapshot(obligation),
            audit_context=audit_context,
            metadata={
                "event_type": str(ObligationEventType.WAIVED),
                "waive_amount": waive_amount,
            },
        )

        return obligation

    @staticmethod
    def supersede_obligation(
        obligation: Obligation,
        new_amount: int,
        audit_context: Optional[dict[str, Any]] = None,
    ) -> Obligation:
        if new_amount < 0:
            raise ValueError("new_amount cannot be negative.")

        if (
            obligation.outstanding_amount < obligation.amount
            or obligation.status != ObligationStatus.OPEN
        ):
            raise ValueError(
                "Only open obligations with no payments allocated can be superseded."
            )

        before_snapshot = ObligationProcessor._obligation_snapshot(obligation)
        old_status = obligation.status

        obligation.locked_by = None
        obligation.outstanding_amount = 0
        obligation.status = ObligationStatus.SUPERSEDED

        old_obligation_log = ObligationActivityLog(
            obligation_id=obligation.id,
            old_status=old_status,
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
            status_updated=(old_status != obligation.status),
        )

        ObligationProcessor.update_obligation(obligation)
        ObligationProcessor.store_obligations_activity_log(old_obligation_log)

        ObligationProcessor._log_obligation_audit(
            action="obligation.superseded",
            obligation=obligation,
            old_status=old_status,
            new_status=obligation.status,
            amount=obligation.amount,
            before_snapshot=before_snapshot,
            after_snapshot=ObligationProcessor._obligation_snapshot(obligation),
            audit_context=audit_context,
            metadata={
                "event_type": str(ObligationEventType.SUPERSEDED),
                "replacement_amount": new_amount,
            },
        )

        new_obligation = ObligationProcessor.add_payable(
            ObligationCreationRequest(
                type=obligation.fee_type,
                amount=new_amount,
                owner_type=obligation.owner_type,
                owner_id=obligation.owner_id,
                status=ObligationStatus.OPEN,
                label=obligation.label,
            ),
            audit_context=audit_context,
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

        if obligation_statuses and all(
            status == ObligationStatus.CLOSED for status in obligation_statuses
        ):
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
