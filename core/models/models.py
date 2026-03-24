from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class PaymentMode(str, Enum):
    ONLINE = "online"
    CHECK = "check"
    COURT = "court"


# Enums
class ObligationStatus(str, Enum):
    OPEN = "open"
    LOCKED = "locked"
    VOIDED = "voided"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"
    WAIVED = "waived"
    CLOSED = "closed"


class ObligationEventType(str, Enum):
    DEBT_CREATED = "obligation.created"
    LOCKED = "obligatuon.locked"
    PAYMENT_AUTHORISED = "obligation.payment_confirmed"
    PAYMENT_SETTLED = "obligation.payment_settled"
    PAYMENT_REFUNDED = "obligation.payment_refunded"
    WAIVED = "obligation.waived"
    GENERAL_UPDATE = "obligation.update"
    PAYMENT_DISPUTE_FUNDS_WITHDRAWN = "obligation.payment_dispute_funds_withdrawn"
    PAYMENT_DISPUTE_FUNDS_RETURN = "obligation.payment_dispute_funds_return"
    PARTIAL_WAIVE = "obligation.partially_waived"
    SUPERSEDED = "obligation.superseded"


class LedgerStage(str, Enum):
    PAYMENT_CONFIRMED = "ledger.payment_confirmed"
    PAYMENT_SETTLED = "ledger.payment_settled"
    PAYMENT_REFUNDED = "ledger.payment_refunded"
    PAYMENT_DISPUTE_FUNDS_WITHDRAWN = "ledger.payment_dispute_funds_withdrawn"
    PAYMENT_DISPUTE_FUNDS_RETURNED = "ledger.payment_dispute_funds_returned"


class TransactionAllocationType(str, Enum):
    CART_ITEM = "cart_item"
    PAYABLE = "payable"


class CartEventType(str, Enum):
    CREATED = "cart.created"
    ITEMS_MODIFIED = "cart.items_modified"
    STATUS_TRANSITIONED = "cart.status_transitioned"
    CART_SETTLED = "cart.settled"
    CHECKEDOUT = "cart.checkedout"
    CART_PAYMENT_REFUNDED = "cart.payment_refunded"
    CART_PAYMENT_CONFIRMED = "cart.payment_confirmed"
    DISPUTE_FUNDS_WITHDRAWN = "cart.dispute_funds_withdrawn"
    DISPUTE_FUNDS_RETURNED = "cart.dispute_funds_returned"


class CartStatus(str, Enum):
    DRAFT = "draft"
    DISPUTED = "disputed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    CHECKOUT = "checkout"
    ABANDONED = "abandoned"
    PAYMENT_SUBMITTED = "payment_submitted"
    PAYMENT_CONFIRMED = "payment_confirmed"
    PAYMENT_SETTLED = "payment_settled"
    SYSTEM_CREATED = "system_created"


class VendorName(str, Enum):
    STRIPE = "stripe"
    CHECKALT = "checkalt"


class VendorEventType(str, Enum):
    PAYMENT_CONFIRMED = "payment_confirmed"
    PAYMENT_SETTLED = "payment_settled"
    PAYMENT_REFUNDED = "payment_refunded"
    PAYMENT_DISPUTE_CREATED = "payment_dispute_created"
    PAYMENT_DISPUTE_FUNDS_WITHDRAWN = "payment_dispute_funds_withdrawn"
    PAYMENT_DISPUTE_FUNDS_RETURNED = "payment_dispute_funds_returned"
    PAYMENT_DISPUTE_LOST = "payment_dispute_lost"


class IssueType(str, Enum):
    INVALID_PAYMENT = "invalid_payment"
    SYSTEM_ERROR = "system_error"


class TransactionBreakdownType(str, Enum):
    PAYMENT = "payment"
    FEE = "fee"


class ObligationLabel(str, Enum):
    CITATION_FEE = "citation_fee"
    LATE_FEE = "late_fee"
    FLAGGING_FEE = "flagging_fee"
    CONVENIENCE_FEE = "convenience_fee"


class ObligationOwnerType(str, Enum):
    CITATION = "citation"
    CART = "cart"
    FLAG = "flag"


class VendorEventProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class RefundProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass
class TransactionBreakdownItemType(str, Enum):
    PAYMENT = "payment"
    FEE = "fee"


# Base class for dataclasses with dict conversion
@dataclass
class BaseDataClass:
    def to_dict(self) -> dict:
        def serialize(obj):
            if isinstance(obj, BaseDataClass):
                return obj.to_dict()
            elif isinstance(obj, list):
                return [serialize(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: serialize(value) for key, value in obj.items()}
            else:
                return obj

        return {key: serialize(value) for key, value in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class RawAllocation(BaseDataClass):
    owner_id: str
    owner_type: str
    label: ObligationLabel
    amount: float


@dataclass
class PayableIdentifiers(BaseDataClass):
    owner_id: str
    owner_type: str
    label: ObligationLabel


@dataclass
class TransactionItemAllocation(BaseDataClass):
    allocation_type: TransactionAllocationType
    amount: int
    owner_id: Optional[str] = None
    owner_type: Optional[str] = None
    label: Optional[str] = None
    cart_item_id: Optional[int] = None


# Models
@dataclass
class Obligation(BaseDataClass):
    owner_id: str
    owner_type: str
    fee_type: str
    label: ObligationLabel
    status: ObligationStatus
    amount: int
    allocated_total: int
    outstanding_amount: int
    overpaid_amount: int
    waived_amount: int = 0
    locked_by: Optional[int] = None
    id: Optional[int] = None


@dataclass
class ObligationActivityLog(BaseDataClass):
    obligation_id: int
    old_status: ObligationStatus
    new_status: ObligationStatus
    status_updated: bool
    allocated_total: int
    outstanding_amount: int
    overpaid_amount: int
    waived_amount: int
    allocated_delta: int
    event_type: ObligationEventType
    locked_by: Optional[int] = None
    ledger_item_id: Optional[int] = None
    vendor_event_id: Optional[int] = None
    transaction_id: Optional[int] = None
    cart_item_id: Optional[int] = None
    payment_mode: Optional[PaymentMode] = None


@dataclass
class ObligationProcessingResult(BaseDataClass):
    obligation: Obligation
    obligation_activity_log: ObligationActivityLog
    citation: Optional["Citation"] = None


@dataclass
class CartItem(BaseDataClass):
    cart_id: int
    amount: float
    obligation: Optional[Obligation] = None
    id: Optional[int] = None


@dataclass
class LedgerAllocationItemInput(BaseDataClass):
    cart_item: CartItem
    amount: float


@dataclass
class LedgerAllocation(BaseDataClass):
    ledger_id: int
    cart_item: CartItem
    amount: float


@dataclass
class TransactionBreakdownItem(BaseDataClass):
    type: TransactionBreakdownItemType
    amount: float
    label: Optional[str] = None


@dataclass
class Cart(BaseDataClass):
    payment_mode: PaymentMode
    vendor: VendorName
    status: CartStatus
    amount: int
    cart_items: List[CartItem] = field(default_factory=list)
    id: Optional[int] = None


@dataclass
class Transaction(BaseDataClass):
    vendor_name: VendorName
    vendor_reference_id: str
    vendor_reference_type: str
    amount: int
    payment_breakdown: List[TransactionBreakdownItem]
    item_allocations: List[TransactionItemAllocation] = field(default_factory=list)
    id: Optional[int] = None


@dataclass
class Cheque(BaseDataClass):
    amount: float
    ids: Dict[str, str]
    metadata: Dict[str, str]


@dataclass
class CartActivityLog(BaseDataClass):
    cart_id: int
    event_type: CartEventType
    old_status: CartStatus
    amount: int
    status_updated: bool
    metadata: Dict[str, any] = field(default_factory=dict)
    new_status: Optional[CartStatus] = None
    vendor_reference_id: Optional[str] = None
    vendor_reference_type: Optional[str] = None
    vendor_event_id: Optional[int] = None


@dataclass
class LedgerItem(BaseDataClass):
    vendor_name: VendorName
    amount: float
    stage: LedgerStage
    type: TransactionBreakdownType
    label: str
    cart: Cart
    confirmed_at: Optional[int] = None
    settled_at: Optional[int] = None
    allocations: Optional[List[LedgerAllocation]] = None
    transaction: Optional[Transaction] = None
    id: Optional[int] = None


@dataclass
class TransactionAttempt(BaseDataClass):
    transaction_result: bool
    failure_reason: Optional[str] = None
    transaction: Optional[Transaction] = None


@dataclass
class VendorEvent(BaseDataClass):
    processing_status: VendorEventProcessingStatus
    event_type: VendorEventType
    vendor_name: VendorName
    metadata: Dict[str, str]
    transaction: Optional[Transaction] = None
    court_adjustment: Optional["CourtAdjustment"] = None
    cart: Optional[Cart] = None
    payment_mode: Optional[PaymentMode] = None
    is_settled: Optional[bool] = None
    id: Optional[int] = None


@dataclass
class TriageRequest(BaseDataClass):
    issue: IssueType
    allocations: Optional[List["LedgerAllocation"]] = None
    obligations: Optional[List[Obligation]] = None
    cart: Optional[Cart] = None
    transaction: Optional[Transaction] = None


@dataclass
class RefundItemAllocation(BaseDataClass):
    cart_item: CartItem
    amount: float


@dataclass
class Refund(BaseDataClass):
    cart: Cart
    refund_amount: int
    transaction: Transaction
    refund_item_allocations: List[RefundItemAllocation]
    vendor_name: VendorName
    processing_status: RefundProcessingStatus
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class CourtAdjustment(BaseDataClass):
    raw_allocation: RawAllocation


@dataclass
class CourtPaymentNotification(BaseDataClass):
    court_adjustment: CourtAdjustment
    status: ObligationStatus


@dataclass
class ObligationCreationRequest(BaseDataClass):
    type: str
    amount: float
    owner_type: ObligationOwnerType
    owner_id: str
    status: ObligationStatus
    label: ObligationLabel


@dataclass
class Citation(BaseDataClass):
    citation_number: str
    ticket_amount: float
    amount_due: int
    amount_paid: float
    payment_status: str
    citation_stage: str
    citation_status: str
    source: str
    payment_date: Optional[str] = None


@dataclass
class CartPayable(BaseDataClass):
    type: str
    amount: float
    status: ObligationStatus
    label: ObligationLabel


@dataclass
class CartCreationRequest:
    status: CartStatus
    vendor: VendorName
    payment_mode: PaymentMode


@dataclass
class AddCartItemsRequest:
    cart: Cart
    obligations: List[Obligation] = field(default_factory=list)
    cart_payables: List[CartPayable] = field(default_factory=list)
    validate: Optional[bool] = False


@dataclass
class ObligationFilterRequest:
    owner_id: Optional[str] = None
    owner_type: Optional[str] = None
    fee_type: Optional[str] = None
    status: Optional[ObligationStatus] = None
    status: Optional[ObligationStatus] = None


@dataclass
class LedgerReportItem:
    payment_date: str
    vendor_name: str
    vendor_reference_type: str
    vendor_reference_id: str
    transaction_id: int
    cart_id: int
    payment_mode: str
    type: str
    label: str
    owner_type: Optional[str]
    owner_id: Optional[str]
    obligation_id: Optional[int]
    obligation_label: Optional[str]

    cart_item_id: Optional[int]

    amount: float


@dataclass
class AccessLog:
    occurred_at: int
    channel: str
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    actor_type: Optional[str] = None
    actor_id: Optional[str] = None
    source: Optional[str] = None
    method: Optional[str] = None
    path_or_operation: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    response_status_code: Optional[int] = None
    status: str = "success"
    duration_ms: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    metadata: str = field(default_factory=lambda: json_dumps({}))


@dataclass
class AuditLog:
    occurred_at: int
    domain: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    actor_type: Optional[str] = None
    actor_id: Optional[str] = None
    source: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None

    cart_id: Optional[str] = None
    cart_item_id: Optional[str] = None
    obligation_id: Optional[str] = None
    transaction_id: Optional[str] = None
    vendor_event_id: Optional[str] = None
    refund_id: Optional[str] = None

    old_status: Optional[str] = None
    new_status: Optional[str] = None
    amount: Optional[int] = None
    status: str = "success"
    reason: Optional[str] = None

    before_snapshot: str = field(default_factory=lambda: json_dumps({}))
    after_snapshot: str = field(default_factory=lambda: json_dumps({}))
    metadata: str = field(default_factory=lambda: json_dumps({}))
