import csv
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from core.models.models import AccessLog, AuditLog


def now_ms() -> int:
    return int(time.time() * 1000)


def json_dumps(value: Any) -> str:
    return json.dumps(
        value if value is not None else {}, separators=(",", ":"), default=str
    )


class CSVLogManager:
    @staticmethod
    def _append_row(file_path: str, fieldnames: list[str], row: dict[str, Any]) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = path.exists()
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)


class AccessLogManager:
    FILE_PATH = "data/access_logs.csv"
    FIELDNAMES = [
        "occurred_at",
        "channel",
        "request_id",
        "correlation_id",
        "actor_type",
        "actor_id",
        "source",
        "method",
        "path_or_operation",
        "target_type",
        "target_id",
        "response_status_code",
        "status",
        "duration_ms",
        "error_code",
        "error_message",
        "metadata",
    ]

    @staticmethod
    def log(entry: AccessLog) -> None:
        CSVLogManager._append_row(
            AccessLogManager.FILE_PATH,
            AccessLogManager.FIELDNAMES,
            asdict(entry),
        )

    @staticmethod
    def log_request(
        *,
        channel: str,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        actor_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        source: Optional[str] = None,
        method: Optional[str] = None,
        path_or_operation: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        response_status_code: Optional[int] = None,
        status: str = "success",
        duration_ms: Optional[int] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        entry = AccessLog(
            occurred_at=now_ms(),
            channel=channel,
            request_id=request_id,
            correlation_id=correlation_id,
            actor_type=actor_type,
            actor_id=actor_id,
            source=source,
            method=method,
            path_or_operation=path_or_operation,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            response_status_code=response_status_code,
            status=status,
            duration_ms=duration_ms,
            error_code=error_code,
            error_message=error_message,
            metadata=json_dumps(metadata or {}),
        )
        AccessLogManager.log(entry)


class AuditLogManager:
    FILE_PATH = "data/audit_logs.csv"
    FIELDNAMES = [
        "occurred_at",
        "domain",
        "action",
        "entity_type",
        "entity_id",
        "actor_type",
        "actor_id",
        "source",
        "request_id",
        "correlation_id",
        "causation_id",
        "cart_id",
        "cart_item_id",
        "obligation_id",
        "transaction_id",
        "vendor_event_id",
        "refund_id",
        "old_status",
        "new_status",
        "amount",
        "status",
        "reason",
        "before_snapshot",
        "after_snapshot",
        "metadata",
    ]

    @staticmethod
    def log(entry: AuditLog) -> None:
        CSVLogManager._append_row(
            AuditLogManager.FILE_PATH,
            AuditLogManager.FIELDNAMES,
            asdict(entry),
        )

    @staticmethod
    def log_event(
        *,
        domain: str,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        actor_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        source: Optional[str] = None,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        cart_id: Optional[int] = None,
        cart_item_id: Optional[int] = None,
        obligation_id: Optional[int] = None,
        transaction_id: Optional[int] = None,
        vendor_event_id: Optional[int] = None,
        refund_id: Optional[int] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        amount: Optional[int] = None,
        status: str = "success",
        reason: Optional[str] = None,
        before_snapshot: Optional[dict[str, Any]] = None,
        after_snapshot: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        entry = AuditLog(
            occurred_at=now_ms(),
            domain=domain,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            actor_type=actor_type,
            actor_id=actor_id,
            source=source,
            request_id=request_id,
            correlation_id=correlation_id,
            cart_id=str(cart_id) if cart_id is not None else None,
            cart_item_id=str(cart_item_id) if cart_item_id is not None else None,
            obligation_id=str(obligation_id) if obligation_id is not None else None,
            transaction_id=str(transaction_id) if transaction_id is not None else None,
            vendor_event_id=(
                str(vendor_event_id) if vendor_event_id is not None else None
            ),
            refund_id=str(refund_id) if refund_id is not None else None,
            old_status=old_status,
            new_status=new_status,
            amount=amount,
            status=status,
            reason=reason,
            before_snapshot=json_dumps(before_snapshot or {}),
            after_snapshot=json_dumps(after_snapshot or {}),
            metadata=json_dumps(metadata or {}),
        )
        AuditLogManager.log(entry)
