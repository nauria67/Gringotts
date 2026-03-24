from core.models.models import VendorEventProcessingStatus, VendorEventType, VendorName
from processors.ledger import Ledger
from processors.payment_orchestrator import PaymentOrchestrator
from processors.transaction_processor import TransactionProcessor
from processors.vendor_event_store import VendorEventStore

vendor_events = VendorEventStore.filter_vendor_events(
    event_type=VendorEventType.PAYMENT_SETTLED,
    processing_status=VendorEventProcessingStatus.PENDING,
    vendor_name=VendorName.STRIPE,
)
for event in vendor_events:
    print(
        f"Found {len(vendor_events)} pending payment settled events for Stripe",
        event,
    )
    PaymentOrchestrator.process_payment_event(event)
