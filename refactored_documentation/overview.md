# Purpose & Rationale

## What is Gringotts?

Gringotts is a **payment orchestration system** that handles all money movement for citation payments. It replaces the legacy citation-centric model with a cart-centric, ledger-driven architecture that supports bulk payments, multiple vendors, partial payments, refunds, disputes, and court adjustments.

---

## Why it exists

The legacy model treated each citation as its own independent payment: one citation, one charge, one Stripe transaction. This caused three problems:

1. **Cost.** Every citation triggered a separate Stripe transaction fee ($0.30 fixed per charge). Paying five citations meant five separate charges.
2. **Inflexibility.** The model couldn't support bundled fees (e.g. a flagging fee attached to a citation), partial payments, or multi-citation checkouts.
3. **Poor auditability.** Payment history was fragmented across individual citations with no unified financial record.

Gringotts solves all three by decoupling *what is owed* from *how it is paid*.

---

## The three core separations

Every concept in Gringotts traces back to one of three layers:

| Layer | Model | What it represents |
| --- | --- | --- |
| **Payment intent** | `Cart` | A user's checkout session — groups one or more obligations into a single payment |
| **Financial liability** | `Obligation` | What someone owes — independent of how or when it is paid |
| **Money movement** | `Ledger` | The immutable record of every financial event — the only source of truth |

These three layers are deliberately independent:

- An obligation exists before a cart is created and persists after the cart is settled.
- The ledger is append-only; it is never modified, only extended.
- The cart manages the *process* of payment, not the *outcome* — the ledger does that.

---

## Payment modes

| Mode | Vendor | Description |
| --- | --- | --- |
| `online` | Stripe | Card payment via the checkout page |
| `check` | CheckAlt | Check or ACH payment |
| `court` | — | Court-issued adjustment or payment |
| `in-person` | — | Leo marks a citation as paid |

---

## Key design principles

- **Event-driven.** All vendor signals drive state transitions asynchronously via a queue.
- **Eventually consistent.** State across carts, obligations, and the ledger converges through async processing — the API returns immediately.
- **Ledger-first.** Financial truth is derived from immutable ledger entries, never from cart or obligation fields.
- **Idempotent.** Every processor safely handles retries and duplicate events via deduplication keys.
- **Vendor-agnostic.** The core pipeline has no vendor imports. Adding a new vendor means implementing a single interface — nothing in the core changes.
- **Fully auditable.** Every state change produces an audit log with before/after snapshots and correlation IDs for end-to-end tracing.

---

## Documentation index

| Document | What it covers |
| --- | --- |
| [System Architecture](https://www.notion.so/System-Architecture-3259ccb8874f80c8aa22efaf5fc0b12a?pvs=21)  | All system components, how they interact, the full system design diagram, and sequence diagrams for every major flow |
| [Core Data Model](https://www.notion.so/Core-Data-Model-3379ccb8874f80178b63e4bf25a44387?pvs=21)  | Every domain model, enum, field table, status lifecycle diagram, and the event→system action mapping |
| [Vendor Integration](https://www.notion.so/Vendor-Integration-3369ccb8874f800bbafaebff94442148?pvs=21)  | Vendor Integration is extracted in a vendor Layer making the processing system vendor agnostic |

External vendors are treated as black-box signal emitters, and all financial state is derived from:
`Vendor Signals → VendorEvent → Event Processor → Ledger → Derived State`
Vendor Integration is extracted in a vendor Layer making the processing system vendor agnostic

# Definition & Context

## 1. Intent Layer (API + Cart)

Handles **user intent and validation**, not financial truth.

### Components

- Gringotts API
- Cart
- CartItem
- Obligation (read + lock only)

### Responsibilities

- Create carts
- Validate payable items
- Add items to cart
- Initiate payment with vendor
- Lock obligations on submission

### Key Principle

> The API does not mutate financial state — it only captures intent.
> 

---

## 2. Financial Processing Layer (Event + Ledger)

The **core system** responsible for all financial correctness.

### Components

- VendorEvent Queue
- Event Processor
- Ledger Manager
- Transaction Store

### Responsibilities

- Ingest vendor signals (webhook / polling / file ingestion)
- Normalize into VendorEvents
- Enrich vendor data
- Create/update Transactions
- Record immutable Ledger entries
- Resolve allocations (money → obligations)
- Update:
    - Cart state
    - Obligation balances

# Implementation Approach

We adopt a pure **event-driven** architecture centered around **VendorEvents**.

`Vendor (black box) → VendorEvent Queue → Event Processor → Ledger (source of truth) → Derived State (Cart, Obligation, Citation)`

---

## 🔹 Key Responsibilities

### Gringotts API (Intent Layer)

- Creates and manages carts
- Validates obligations
- Initiates vendor payment
- Locks obligations on submission

> Does not mutate financial state
> 

---

### Event Processor (Core Engine)

- Consumes VendorEvents
- Resolves allocations
- Triggers ledger writes
- Updates Cart and Obligation

---

### Ledger Manager

- Writes immutable ledger entries
- Maintains allocation records
- Acts as the financial source of truth

---

---

## In-Person Payment Flow (Updated)

### Old

`LEO → API → immediate DB update`
**New**

`LEO → API → emit vendor signal → VendorEvent Queue → Event Processor → Ledger → Obligation update`

---

# 🎯 Target Outcomes

### 1. Stripe Optimisation

- One transaction per cart (not per citation)
- Reduced fixed fees

---

### 2. Financial Correctness

- Ledger is the single source of truth
- All state derived from immutable records

---

### 3. Operational Resilience

Supports:

- partial payments
- refunds
- disputes
- mismatched allocations

Handled via:

- async processing
- idempotent event handling

---

### 4. Unified Financial History

All flows are traceable:

`Transaction -> VendorEvent → Ledger → Allocation → Obligation`

---

# Metrics Derived from the System

Because all state flows through **VendorEvents → Ledger**, we can derive robust metrics.

---

## 🔹 Processing & System Health

- Event processing latency (signal → ledger)
- Queue lag (time in VendorEvent Queue)
- Event throughput (events/sec)
- Failure / retry rate

---

## 🔹 Payment Metrics (Ledger-Based)

- Total payment volume
- Net revenue (payments − fees − refunds)
- Fee breakdown (Stripe, convenience, etc.)
- Refund volume
- Dispute impact

---

## 🔹 Cart & Checkout Metrics

- Cart conversion rate (`submitted / checkout`)
- Cart abandonment rate
- Average cart value
- Multi-item cart rate

---

## 🔹 Obligation Metrics

- Collection rate (paid vs outstanding)
- Outstanding balance
- Overpayment volume
- Partial payment rate