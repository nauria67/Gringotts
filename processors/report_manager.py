import csv
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List

from core.models.models import LedgerReportItem
from processors.ledger import Ledger


class ReportManager:
    report_csv_path = "data/ledger_report.csv"

    @staticmethod
    def store(ledger_report: List[LedgerReportItem]):
        os.makedirs(os.path.dirname(ReportManager.report_csv_path), exist_ok=True)

        fieldnames = [
            "payment_date",
            "vendor_name",
            "vendor_reference_type",
            "vendor_reference_id",
            "transaction_id",
            "cart_id",
            "payment_mode",
            "type",
            "label",
            "owner_type",
            "owner_id",
            "obligation_id",
            "obligation_label",
            "cart_item_id",
            "amount",
        ]

        with open(ReportManager.report_csv_path, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            for item in ledger_report:
                row = asdict(item)

                # normalize enums / objects to plain values if needed
                normalized_row = {
                    key: getattr(value, "value", value) for key, value in row.items()
                }
                writer.writerow(normalized_row)

    @staticmethod
    def generate_report() -> List[LedgerReportItem]:
        report_data: List[LedgerReportItem] = []

        ledger = Ledger.read_ledger_from_csv()
        settled_ledger_items = [item for item in ledger if item.settled_at is not None]

        for ledger_item in settled_ledger_items:
            transaction = ledger_item.transaction
            cart = ledger_item.cart
            # epoch millisec to datetime utc
            payment_date = datetime.fromtimestamp(
                ledger_item.settled_at / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S")

            allocations = ledger_item.allocations or []

            if allocations:
                for allocation in allocations:
                    obligation = (
                        allocation.cart_item.obligation
                        if allocation.cart_item
                        else None
                    )

                    report_item = LedgerReportItem(
                        payment_date=payment_date,
                        vendor_name=ledger_item.vendor_name,
                        vendor_reference_type=(
                            transaction.vendor_reference_type if transaction else None
                        ),
                        vendor_reference_id=(
                            transaction.vendor_reference_id if transaction else None
                        ),
                        transaction_id=transaction.id if transaction else None,
                        cart_id=cart.id if cart else None,
                        payment_mode=cart.payment_mode,
                        type=ledger_item.type,
                        label=ledger_item.label,
                        owner_type=obligation.owner_type if obligation else None,
                        owner_id=obligation.owner_id if obligation else None,
                        obligation_id=obligation.id if obligation else None,
                        obligation_label=obligation.label if obligation else None,
                        cart_item_id=(
                            allocation.cart_item.id if allocation.cart_item else None
                        ),
                        amount=allocation.amount,
                    )
                    report_data.append(report_item)
            else:
                report_item = LedgerReportItem(
                    payment_date=payment_date,
                    vendor_name=ledger_item.vendor_name,
                    vendor_reference_type=(
                        transaction.vendor_reference_type if transaction else None
                    ),
                    vendor_reference_id=(
                        transaction.vendor_reference_id if transaction else None
                    ),
                    transaction_id=transaction.id if transaction else None,
                    cart_id=cart.id if cart else None,
                    payment_mode=cart.payment_mode,
                    type=ledger_item.type,
                    label=ledger_item.label,
                    owner_type=None,
                    owner_id=None,
                    obligation_id=None,
                    obligation_label=None,
                    cart_item_id=None,
                    amount=ledger_item.amount,
                )
                report_data.append(report_item)

        ReportManager.store(report_data)
        return report_data
