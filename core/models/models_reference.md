# Gringotts Data Models

---

## Obligation

### ObligationStatus

| Value | Description |
| --- | --- |
| `open` | Obligation is active and has an outstanding balance |
| `locked` | Obligation is reserved for an in-progress payment (locked by a cart) |
| `closed` | Obligation is fully resolved — either fully paid or the remainder was waived |
| `waived` | Obligation was waived in full; no payment was made |
| `superseded` | Obligation has been replaced by a new obligation with an adjusted amount |
| `voided` | Obligation was cancelled entirely |
| `disputed` | Obligation is under active dispute |

#### Obligation Status Transitions

```
[new] ──────────────────────────── open
         │                           │                           │
    lock_obligations          waive_obligation           supersede_obligation
    (cart checkout)           (no payments made)         (no payments made)
         │                           │                           │
         ▼                           ▼                           ▼
       locked                     waived                    superseded
         │                                             (new obligation created
         │                                              with adjusted amount)
   payment event
   (confirmed/settled/
    refunded/dispute)
         │
         ├─── outstanding > 0 ──► open  (unlocked)
         │
         └─── outstanding = 0 ──► closed

open/locked + partial payment ──► waive_partially_paid_obligation ──► closed
                                   (waives remaining balance)
```

> `superseded`, `voided`, and `waived` are terminal statuses — obligations in these states are excluded from payment eligibility checks.

---

### ObligationEventType

| Value | Description |
| --- | --- |
| `obligation.created` | A new obligation was created |
| `obligation.locked` | Obligation was locked to a cart in preparation for payment |
| `obligation.payment_confirmed` | Payment confirmed; obligation allocation updated |
| `obligation.payment_settled` | Payment settled; allocation finalised |
| `obligation.payment_refunded` | Payment was refunded; allocation reversed |
| `obligation.waived` | Obligation was waived in full (no prior payments) |
| `obligation.partially_waived` | Remaining balance was waived after partial payment |
| `obligation.update` | General update — no status change |
| `obligation.payment_dispute_funds_withdrawn` | Dispute opened; funds withdrawn from merchant |
| `obligation.payment_dispute_funds_return` | Dispute resolved; funds returned to merchant |
| `obligation.superseded` | Obligation replaced by a new one with an adjusted amount |

---

### ObligationLabel

| Value | Description |
| --- | --- |
| `citation_fee` | Primary fee associated with a citation |
| `late_fee` | Late payment penalty |
| `flagging_fee` | Fee for flagging a vehicle |
| `convenience_fee` | Vendor-charged processing or convenience fee |

---

### ObligationOwnerType

| Value | Description |
| --- | --- |
| `citation` | Obligation belongs to a citation |
| `cart` | Obligation belongs to a cart (e.g. a convenience fee added at checkout) |
| `flag` | Obligation belongs to a vehicle flag |

---

### Obligation

| Field | Type | Required |
| --- | --- | --- |
| owner_id | string | yes |
| owner_type | `citation` \| `cart` \| `flag` | yes |
| fee_type | string | yes |
| label | ObligationLabel | yes |
| status | ObligationStatus | yes |
| amount | int | yes |
| allocated_total | int | yes |
| outstanding_amount | int | yes |
| overpaid_amount | int | yes |
| waived_amount | int | default `0` |
| locked_by | int | optional — cart ID that holds the lock |
| id | int | optional |

> `outstanding_amount = amount − allocated_total`. When `outstanding_amount` reaches `0`, the obligation moves to `closed`. When `allocated_total > amount`, the excess is captured in `overpaid_amount`.

---

### ObligationActivityLog

| Field | Type | Required |
| --- | --- | --- |
| obligation_id | int | yes |
| old_status | ObligationStatus | yes |
| new_status | ObligationStatus | yes |
| status_updated | bool | yes |
| allocated_total | int | yes |
| outstanding_amount | int | yes |
| overpaid_amount | int | yes |
| waived_amount | int | yes |
| allocated_delta | int | yes — change in allocated_total for this event |
| event_type | ObligationEventType | yes |
| locked_by | int | optional |
| ledger_item_id | int | optional |
| vendor_event_id | int | optional |
| transaction_id | int | optional |
| cart_item_id | int | optional |
| payment_mode | `online` \| `check` \| `court` | optional |

---

### ObligationProcessingResult

| Field | Type | Required |
| --- | --- | --- |
| obligation | Obligation | yes |
| obligation_activity_log | ObligationActivityLog | yes |
| citation | Citation | optional |

---

### ObligationCreationRequest

| Field | Type | Required |
| --- | --- | --- |
| type | string | yes |
| amount | float | yes |
| owner_type | `citation` \| `cart` \| `flag` | yes |
| owner_id | string | yes |
| status | ObligationStatus | yes |
| label | ObligationLabel | yes |

---

### ObligationFilterRequest

| Field | Type | Required |
| --- | --- | --- |
| owner_id | string | optional |
| owner_type | string | optional |
| fee_type | string | optional |
| status | ObligationStatus | optional |

---

## Cart

### CartStatus

| Value | Description |
| --- | --- |
| `draft` | Cart created but not yet populated or submitted |
| `system_created` | Cart auto-created by the system (e.g. for check or court payments) |
| `abandoned` | Cart was abandoned during checkout before payment was submitted |
| `checkout` | Cart has been checked out and is ready for payment submission |
| `payment_submitted` | Payment submitted to the vendor; associated obligations are locked |
| `payment_confirmed` | Vendor has confirmed receipt of payment |
| `payment_settled` | Payment has been fully settled and cleared |
| `disputed` | Payment is under dispute; funds have been withdrawn by the vendor |
| `dispute_lost` | Dispute resolved against the merchant; funds permanently taken |

#### Cart Status Transitions

```
[new] ──────────────────────────────── draft / system_created
                                                  │
                                          checkout_cart
                                                  │
                                                  ▼
                                              checkout
                                                  │
                                         submit_payment
                                       (locks obligations)
                                                  │
                                                  ▼
                                        payment_submitted
                                                  │
                              ┌───────────────────┤
                    payment_confirmed       (vendor event)
                              │
                              ▼
                      payment_confirmed
                              │
                     payment_settled
                              │
                              ▼
                       payment_settled ◄──── dispute_funds_returned
                              │                        ▲
                    payment_refunded          dispute_funds_withdrawn
                    (cart.refund_amount            │
                     incremented,              disputed
                     status unchanged)             │
                                           dispute_lost (terminal)
```

> Refunds do not change cart status. Each `payment_refunded` vendor event increments `cart.refund_amount`. To see which items were refunded, query `RefundItemAllocation` records for the cart.
>
> Disputes cover the entire cart. Won → `payment_settled` (funds returned). Lost → `dispute_lost` (terminal, funds permanently taken).

---

### CartEventType

| Value | Description |
| --- | --- |
| `cart.created` | Cart was created |
| `cart.items_modified` | Items were added to or removed from the cart |
| `cart.status_transitioned` | Cart status changed (e.g. on payment submission) |
| `cart.checkedout` | Cart was checked out by the user |
| `cart.settled` | Cart payment was fully settled |
| `cart.payment_confirmed` | Vendor confirmed the cart payment |
| `cart.payment_refunded` | Cart payment was refunded; `cart.refund_amount` incremented |
| `cart.dispute_funds_withdrawn` | Dispute filed; funds withdrawn from the merchant |
| `cart.dispute_funds_returned` | Dispute resolved in merchant's favour; funds returned |
| `cart.dispute_lost` | Dispute resolved against the merchant; `dispute_lost` status set |

---

### Cart

| Field | Type | Required |
| --- | --- | --- |
| payment_mode | `online` \| `check` \| `court` | yes |
| vendor | `stripe` \| `checkalt` | yes |
| status | CartStatus | yes |
| amount | int | yes |
| cart_items | List[CartItem] | default `[]` |
| refund_amount | int | default `0` — cumulative total refunded; compare against `amount` to determine full vs partial refund |
| id | int | optional |

---

### CartItem

| Field | Type | Required |
| --- | --- | --- |
| cart_id | int | yes |
| amount | float | yes |
| obligation | Obligation | optional |
| id | int | optional |

> To determine which items were refunded, query `RefundItemAllocation` records linked to this cart. Cart items can only be refunded in full.

---

### CartActivityLog

| Field | Type | Required |
| --- | --- | --- |
| cart_id | int | yes |
| event_type | CartEventType | yes |
| old_status | CartStatus | yes |
| amount | int | yes |
| status_updated | bool | yes |
| metadata | Dict | default `{}` |
| new_status | CartStatus | optional |
| vendor_reference_id | string | optional |
| vendor_reference_type | string | optional |
| vendor_event_id | int | optional |

---

### CartCreationRequest

| Field | Type | Required |
| --- | --- | --- |
| status | CartStatus | yes |
| vendor | `stripe` \| `checkalt` | yes |
| payment_mode | `online` \| `check` \| `court` | yes |

---

### AddCartItemsRequest

| Field | Type | Required |
| --- | --- | --- |
| cart | Cart | yes |
| obligations | List[Obligation] | default `[]` |
| cart_payables | List[CartPayable] | default `[]` |
| validate | bool | default `false` |

---

### CartPayable

A lightweight obligation descriptor used when adding fee-type items (e.g. convenience fees) directly to a cart without a pre-existing obligation.

| Field | Type | Required |
| --- | --- | --- |
| type | string | yes |
| amount | float | yes |
| status | ObligationStatus | yes |
| label | ObligationLabel | yes |

---

## Transaction

### TransactionBreakdownType

| Value | Description |
| --- | --- |
| `payment` | Represents the principal payment amount |
| `fee` | Represents a fee charged (e.g. a convenience fee) |

---

### TransactionAllocationType

| Value | Description |
| --- | --- |
| `cart_item` | Allocation is tied to a specific cart item by ID |
| `payable` | Allocation is resolved by matching obligation owner/label identifiers |

---

### Transaction

Represents a single payment transaction received from a vendor, including how the total amount breaks down and how it is allocated across obligations.

| Field | Type | Required |
| --- | --- | --- |
| vendor_name | `stripe` \| `checkalt` | yes |
| vendor_reference_id | string | yes |
| vendor_reference_type | string | yes |
| amount | int | yes |
| payment_breakdown | List[TransactionBreakdownItem] | yes |
| item_allocations | List[TransactionItemAllocation] | default `[]` |
| id | int | optional |

---

### TransactionBreakdownItem

A single line in the payment breakdown (e.g. one entry for the payment amount, one for the fee).

| Field | Type | Required |
| --- | --- | --- |
| type | `payment` \| `fee` | yes |
| amount | float | yes |
| label | string | optional |

---

### TransactionItemAllocation

Specifies how a portion of a transaction is allocated to a particular obligation or cart item.

| Field | Type | Required |
| --- | --- | --- |
| allocation_type | `cart_item` \| `payable` | yes |
| amount | int | yes |
| owner_id | string | optional — required when allocation_type is `payable` |
| owner_type | string | optional — required when allocation_type is `payable` |
| label | string | optional — required when allocation_type is `payable` |
| cart_item_id | int | optional — required when allocation_type is `cart_item` |

---

### TransactionAttempt

Result of an attempted payment transaction with a vendor.

| Field | Type | Required |
| --- | --- | --- |
| transaction_result | bool | yes |
| failure_reason | string | optional |
| transaction | Transaction | optional |

---

## Ledger

### LedgerStage

| Value | Description |
| --- | --- |
| `ledger.payment_confirmed` | Recorded when a vendor confirms payment |
| `ledger.payment_settled` | Recorded when payment clears/settles |
| `ledger.payment_refunded` | Recorded when a refund is issued |
| `ledger.payment_dispute_funds_withdrawn` | Recorded when dispute funds are withdrawn |
| `ledger.payment_dispute_funds_returned` | Recorded when dispute is resolved and funds returned |

---

### LedgerItem

A single line item in the financial ledger, tied to a specific cart and stage of a payment lifecycle.

| Field | Type | Required |
| --- | --- | --- |
| vendor_name | `stripe` \| `checkalt` | yes |
| amount | float | yes |
| stage | LedgerStage | yes |
| type | `payment` \| `fee` | yes |
| label | string | yes |
| cart | Cart | yes |
| confirmed_at | int (timestamp) | optional |
| settled_at | int (timestamp) | optional |
| allocations | List[LedgerAllocation] | optional |
| transaction | Transaction | optional |
| id | int | optional |

---

### LedgerAllocation

Maps a ledger item to a specific cart item, recording how much of the ledger amount is attributed to each obligation.

| Field | Type | Required |
| --- | --- | --- |
| ledger_id | int | yes |
| cart_item | CartItem | yes |
| amount | float | yes |

---

### LedgerAllocationItemInput

Input structure used when recording a new ledger event.

| Field | Type | Required |
| --- | --- | --- |
| cart_item | CartItem | yes |
| amount | float | yes |

---

### LedgerReportItem

Flattened view of a ledger entry used for reporting.

| Field | Type | Required |
| --- | --- | --- |
| payment_date | string | yes |
| vendor_name | string | yes |
| vendor_reference_type | string | yes |
| vendor_reference_id | string | yes |
| transaction_id | int | yes |
| cart_id | int | yes |
| payment_mode | string | yes |
| type | string | yes |
| label | string | yes |
| amount | float | yes |
| owner_type | string | optional |
| owner_id | string | optional |
| obligation_id | int | optional |
| obligation_label | string | optional |
| cart_item_id | int | optional |

---

## Vendor Events

### VendorName

| Value | Description |
| --- | --- |
| `stripe` | Stripe — online card payment gateway |
| `checkalt` | CheckAlt — check/ACH payment processor |

---

### VendorEventType

| Value | Description |
| --- | --- |
| `payment_confirmed` | Vendor confirms the payment has been received |
| `payment_settled` | Vendor confirms the payment has cleared/settled |
| `payment_refunded` | Vendor has processed a refund |
| `payment_dispute_created` | A chargeback or dispute has been opened |
| `payment_dispute_funds_withdrawn` | Disputed funds have been withdrawn from the merchant |
| `payment_dispute_funds_returned` | Dispute resolved in merchant's favour; funds returned |
| `payment_dispute_lost` | Dispute resolved against the merchant; funds not returned |

#### Vendor Event → System Actions

| Vendor Event | Cart Status | Obligation Event | Ledger Stage |
| --- | --- | --- | --- |
| `payment_confirmed` | `payment_confirmed` | `obligation.payment_confirmed` | `ledger.payment_confirmed` |
| `payment_settled` | `payment_settled` | `obligation.payment_settled` | `ledger.payment_settled` |
| `payment_refunded` | _(no change — `refund_amount` incremented)_ | `obligation.payment_refunded` | `ledger.payment_refunded` |
| `payment_dispute_funds_withdrawn` | `disputed` | `obligation.payment_dispute_funds_withdrawn` | `ledger.payment_dispute_funds_withdrawn` |
| `payment_dispute_funds_returned` | `payment_settled` | `obligation.payment_dispute_funds_return` | `ledger.payment_dispute_funds_returned` |
| `payment_dispute_lost` | `dispute_lost` | _(no obligation event)_ | _(no ledger entry)_ |

---

### VendorEventProcessingStatus

| Value | Description |
| --- | --- |
| `pending` | Event has been received but not yet processed |
| `processed` | Event was successfully processed |
| `failed` | Event processing encountered an error |

---

### VendorEvent

Inbound event from a payment vendor, driving downstream updates to carts, obligations, and the ledger.

| Field | Type | Required |
| --- | --- | --- |
| processing_status | VendorEventProcessingStatus | yes |
| event_type | VendorEventType | yes |
| vendor_name | `stripe` \| `checkalt` | yes |
| metadata | Dict[string, string] | yes |
| transaction | Transaction | optional |
| court_adjustment | CourtAdjustment | optional |
| cart | Cart | optional |
| payment_mode | `online` \| `check` \| `court` | optional |
| is_settled | bool | optional |
| id | int | optional |

---

## Payment

### PaymentMode

| Value | Description |
| --- | --- |
| `online` | Online card payment (processed via Stripe) |
| `check` | Payment by check (processed via CheckAlt) |
| `court` | Court-issued payment or adjustment |

---

### Cheque

Represents a physical check received as payment.

| Field | Type | Required |
| --- | --- | --- |
| amount | float | yes |
| ids | Dict[string, string] | yes |
| metadata | Dict[string, string] | yes |

---

## Refund

### RefundProcessingStatus

| Value | Description |
| --- | --- |
| `pending` | Refund has been initiated but not yet processed by the vendor |
| `processed` | Refund has been successfully completed |
| `failed` | Refund processing failed |

---

### Refund

| Field | Type | Required |
| --- | --- | --- |
| cart | Cart | yes |
| refund_amount | int | yes |
| transaction | Transaction | yes |
| refund_item_allocations | List[RefundItemAllocation] | yes |
| vendor_name | `stripe` \| `checkalt` | yes |
| processing_status | RefundProcessingStatus | yes |
| metadata | Dict | default `{}` |

---

### RefundItemAllocation

Records which cart item was refunded and the amount. Cart items can only be refunded in full — this is the source of truth for item-level refund status.

| Field | Type | Required |
| --- | --- | --- |
| cart_item | CartItem | yes |
| amount | float | yes |

---

## Court Payments

### CourtAdjustment

Wraps a court-issued raw allocation, used when a court processes a payment directly against an obligation.

| Field | Type | Required |
| --- | --- | --- |
| raw_allocation | RawAllocation | yes |

---

### CourtPaymentNotification

Notification of a court payment outcome, including the resulting obligation status.

| Field | Type | Required |
| --- | --- | --- |
| court_adjustment | CourtAdjustment | yes |
| status | ObligationStatus | yes |

---

### RawAllocation

A low-level allocation input used in court payment flows, identifying an obligation by its owner and label.

| Field | Type | Required |
| --- | --- | --- |
| owner_id | string | yes |
| owner_type | string | yes |
| label | ObligationLabel | yes |
| amount | float | yes |

---

### PayableIdentifiers

Minimal identifiers for looking up an obligation by its owner and fee label without needing its ID.

| Field | Type | Required |
| --- | --- | --- |
| owner_id | string | yes |
| owner_type | string | yes |
| label | ObligationLabel | yes |

---

## Citation

| Field | Type | Required |
| --- | --- | --- |
| citation_number | string | yes |
| ticket_amount | float | yes |
| amount_due | int | yes |
| amount_paid | float | yes |
| payment_status | string | yes |
| citation_stage | string | yes |
| citation_status | string | yes |
| source | string | yes |
| payment_date | string | optional |

---

## Triage

### IssueType

| Value | Description |
| --- | --- |
| `invalid_payment` | Payment was invalid or could not be matched to obligations |
| `system_error` | An internal processing error occurred |

---

### TriageRequest

Used to flag and investigate payment anomalies or system errors.

| Field | Type | Required |
| --- | --- | --- |
| issue | `invalid_payment` \| `system_error` | yes |
| allocations | List[LedgerAllocation] | optional |
| obligations | List[Obligation] | optional |
| cart | Cart | optional |
| transaction | Transaction | optional |

---

## Activity & Audit Logs

### AccessLog

Records every inbound API or channel request for observability.

| Field | Type | Required |
| --- | --- | --- |
| occurred_at | int (timestamp) | yes |
| channel | string | yes |
| request_id | string | optional |
| correlation_id | string | optional |
| actor_type | string | optional |
| actor_id | string | optional |
| source | string | optional |
| method | string | optional |
| path_or_operation | string | optional |
| target_type | string | optional |
| target_id | string | optional |
| response_status_code | int | optional |
| status | string | default `"success"` |
| duration_ms | int | optional |
| error_code | string | optional |
| error_message | string | optional |
| metadata | JSON string | default `{}` |

---

### AuditLog

Records domain-level state changes for compliance and traceability. Every significant mutation (obligation created, cart settled, payment confirmed, etc.) produces an audit log entry.

| Field | Type | Required |
| --- | --- | --- |
| occurred_at | int (timestamp) | yes |
| domain | string | yes — e.g. `obligation`, `cart` |
| action | string | yes — e.g. `obligation.created`, `cart.payment_confirmed` |
| entity_type | string | yes |
| entity_id | string | optional |
| actor_type | string | optional |
| actor_id | string | optional |
| source | string | optional — originating processor, e.g. `obligation_processor` |
| request_id | string | optional |
| correlation_id | string | optional |
| causation_id | string | optional |
| cart_id | string | optional |
| cart_item_id | string | optional |
| obligation_id | string | optional |
| transaction_id | string | optional |
| vendor_event_id | string | optional |
| refund_id | string | optional |
| old_status | string | optional |
| new_status | string | optional |
| amount | int | optional |
| status | string | default `"success"` |
| reason | string | optional |
| before_snapshot | JSON string | default `{}` |
| after_snapshot | JSON string | default `{}` |
| metadata | JSON string | default `{}` |
