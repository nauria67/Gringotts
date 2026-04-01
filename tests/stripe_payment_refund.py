from core.models.models import VendorEventProcessingStatus, VendorEventType, VendorName
from processors.vendor_event_worker import VendorEventWorker

VendorEventWorker.process_pending_vendor_events(
    event_type=VendorEventType.PAYMENT_REFUNDED,
    processing_status=VendorEventProcessingStatus.PENDING,
    vendor_name=VendorName.STRIPE,
    worker_name="vendor_event_consumer",
)
