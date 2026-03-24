from core.models.models import (
    CartCreationRequest,
    VendorEvent,
    VendorEventProcessingStatus,
    VendorEventType,
    VendorName,
)
from processors.cart_processor import CartProcessor
from processors.ledger import Ledger
from processors.obligation_processor import ObligationProcessor
from processors.payment_orchestrator import PaymentOrchestrator
from processors.transaction_processor import TransactionProcessor
from processors.vendor_event_store import VendorEventStore

vendor_events = VendorEventStore.filter_vendor_events(
    event_type=VendorEventType.PAYMENT_SETTLED,
    processing_status=VendorEventProcessingStatus.PENDING,
    vendor_name=VendorName.CHECKALT,
)
for event in vendor_events:
    if event.id == 3:
        PaymentOrchestrator.process_payment_event(event)
