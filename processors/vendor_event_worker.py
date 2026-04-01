from core.models.models import VendorEventProcessingStatus, VendorEventType, VendorName
from processors.log_manager import AccessLogManager, AuditLogManager
from processors.payment_orchestrator import PaymentOrchestrator
from processors.vendor_event_store import VendorEventStore


class VendorEventWorker:
    @staticmethod
    def _build_correlation_id(event):
        if getattr(event, "cart", None):
            return f"cart_payment:{event.cart.id}"
        return f"vendor_event:{event.id}"

    @staticmethod
    def _build_audit_context(
        event, worker_name: str, request_id: str, correlation_id: str
    ):
        return {
            "actor_type": "system",
            "actor_id": worker_name,
            "source": worker_name,
            "request_id": request_id,
            "correlation_id": correlation_id,
            "causation_id": f"worker_batch:{worker_name}",
        }

    @staticmethod
    def process_pending_vendor_events(
        *,
        event_type: VendorEventType,
        processing_status: VendorEventProcessingStatus,
        vendor_name: VendorName,
        worker_name: str,
        event_filter_fn=None,
    ):
        vendor_events = VendorEventStore.filter_vendor_events(
            event_type=event_type,
            processing_status=processing_status,
            vendor_name=vendor_name,
        )

        if event_filter_fn:
            vendor_events = [event for event in vendor_events if event_filter_fn(event)]

        for event in vendor_events:
            correlation_id = VendorEventWorker._build_correlation_id(event)
            request_id = f"worker_event:{event.id}"
            audit_context = VendorEventWorker._build_audit_context(
                event=event,
                worker_name=worker_name,
                request_id=request_id,
                correlation_id=correlation_id,
            )

            AuditLogManager.log_event(
                domain="vendor_event",
                action="vendor_event.processing_dispatched",
                entity_type="vendor_event",
                entity_id=str(event.id),
                actor_type="system",
                actor_id=worker_name,
                source=worker_name,
                request_id=request_id,
                correlation_id=correlation_id,
                causation_id=f"worker_batch:{worker_name}",
                cart_id=event.cart.id if getattr(event, "cart", None) else None,
                transaction_id=(
                    event.transaction.id
                    if getattr(event, "transaction", None)
                    else None
                ),
                vendor_event_id=event.id,
                status="success",
                before_snapshot={
                    "id": event.id,
                    "processing_status": event.processing_status.value,
                    "event_type": event.event_type.value,
                    "vendor_name": event.vendor_name.value,
                },
                after_snapshot={
                    "id": event.id,
                    "processing_status": event.processing_status.value,
                    "event_type": event.event_type.value,
                    "vendor_name": event.vendor_name.value,
                },
                metadata={"worker": worker_name},
            )

            try:
                PaymentOrchestrator.process_payment_event(
                    event,
                    audit_context=audit_context,
                )

                AccessLogManager.log_request(
                    channel="worker",
                    request_id=request_id,
                    correlation_id=correlation_id,
                    actor_type="system",
                    actor_id=worker_name,
                    source=worker_name,
                    method="CONSUME",
                    path_or_operation="process_payment_event",
                    target_type="vendor_event",
                    target_id=str(event.id),
                    response_status_code=200,
                    status="success",
                    metadata={
                        "event_type": event.event_type.value,
                        "vendor_name": event.vendor_name.value,
                    },
                )

            except Exception as e:
                AccessLogManager.log_request(
                    channel="worker",
                    request_id=request_id,
                    correlation_id=correlation_id,
                    actor_type="system",
                    actor_id=worker_name,
                    source=worker_name,
                    method="CONSUME",
                    path_or_operation="process_payment_event",
                    target_type="vendor_event",
                    target_id=str(event.id),
                    response_status_code=500,
                    status="failure",
                    error_code="VENDOR_EVENT_PROCESSING_FAILED",
                    error_message=str(e),
                    metadata={
                        "event_type": event.event_type.value,
                        "vendor_name": event.vendor_name.value,
                    },
                )

                AuditLogManager.log_event(
                    domain="vendor_event",
                    action="vendor_event.processing_dispatched",
                    entity_type="vendor_event",
                    entity_id=str(event.id),
                    actor_type="system",
                    actor_id=worker_name,
                    source=worker_name,
                    request_id=request_id,
                    correlation_id=correlation_id,
                    causation_id=f"worker_batch:{worker_name}",
                    cart_id=event.cart.id if getattr(event, "cart", None) else None,
                    transaction_id=(
                        event.transaction.id
                        if getattr(event, "transaction", None)
                        else None
                    ),
                    vendor_event_id=event.id,
                    status="failure",
                    reason=str(e),
                    metadata={
                        "worker": worker_name,
                        "error": str(e),
                    },
                )
                raise
