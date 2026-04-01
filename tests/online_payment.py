import csv
import time
from typing import List

from core.models.models import (
    AddCartItemsRequest,
    CartCreationRequest,
    CartPayable,
    CartStatus,
    Citation,
    ObligationFilterRequest,
    ObligationLabel,
    ObligationStatus,
    PaymentMode,
    VendorName,
)
from processors.cart_processor import CartProcessor
from processors.log_manager import AccessLogManager, AuditLogManager
from processors.obligation_processor import ObligationProcessor


def fetch_data():
    citations = []
    with open("/Users/obvio/Desktop/gringotts/data/citations.csv", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            citations.append(
                Citation(
                    citation_number=row["citation_number"],
                    ticket_amount=float(row["citation_due_amount"]),
                    amount_due=float(row["citation_due_amount"]),
                    amount_paid=float(row["citation_amount_paid"]),
                    payment_status=row["payment_status"],
                    citation_stage=row["citation_stage"],
                    citation_status=row["citation_status"],
                    payment_date=row.get("latest_payment_date"),
                    source=row["payment_source"],
                )
            )

    payment_pending_citations = [
        c
        for c in citations
        if c.citation_stage == "payment" and c.citation_status == "pending"
    ]

    obligations = ObligationProcessor.read_obligations_from_csv()
    return payment_pending_citations, obligations


def _now_ms() -> int:
    return int(time.time() * 1000)


def _build_checkout_request_id(citation_numbers: List[str]) -> str:
    return f"req_checkout_{'-'.join(citation_numbers)}_{_now_ms()}"


def _build_submit_request_id(cart_id: int) -> str:
    return f"req_submit_{cart_id}_{_now_ms()}"


def _build_correlation_id_for_cart(cart_id: int) -> str:
    return f"cart_payment:{cart_id}"


def _build_audit_context(
    *,
    actor_type: str,
    actor_id: str,
    source: str,
    request_id: str,
    correlation_id: str,
    causation_id: str,
) -> dict:
    return {
        "actor_type": actor_type,
        "actor_id": actor_id,
        "source": source,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
    }


def pay_online(citation_numbers: List[str]):
    # -----------------------------
    # First API call: checkout cart
    # -----------------------------
    checkout_request_id = _build_checkout_request_id(citation_numbers)
    checkout_start = time.time()

    try:
        all_citations, obligations = fetch_data()
        citations = [c for c in all_citations if c.citation_number in citation_numbers]

        obligation_processor = ObligationProcessor()
        filtered_obligations = []

        for citation in citations:
            filtered_obligations_temp = obligation_processor.filter_obligations(
                obligations,
                ObligationFilterRequest(
                    owner_type="citation",
                    owner_id=citation.citation_number,
                    status=ObligationStatus.OPEN,
                ),
            )
            filtered_obligations.extend(filtered_obligations_temp)

        cart = CartProcessor.create_cart(
            CartCreationRequest(
                status=CartStatus.DRAFT,
                vendor=VendorName.STRIPE,
                payment_mode=PaymentMode.ONLINE,
            ),
            audit_context={
                "actor_type": "user",
                "actor_id": "demo_user",
                "source": "online_payment_api",
                "request_id": checkout_request_id,
                "correlation_id": None,
                "causation_id": f"http_request:{checkout_request_id}",
            },
        )

        correlation_id = _build_correlation_id_for_cart(cart.id)

        checkout_audit_context = _build_audit_context(
            actor_type="user",
            actor_id="demo_user",
            source="online_payment_api",
            request_id=checkout_request_id,
            correlation_id=correlation_id,
            causation_id=f"http_request:{checkout_request_id}",
        )

        AuditLogManager.log_event(
            domain="payment",
            action="online_payment.requested",
            entity_type="cart",
            entity_id=str(cart.id),
            actor_type="user",
            actor_id="demo_user",
            source="online_payment_api",
            request_id=checkout_request_id,
            correlation_id=correlation_id,
            causation_id=f"http_request:{checkout_request_id}",
            cart_id=cart.id,
            amount=int(sum(c.amount_due for c in citations) + 400),
            status="success",
            before_snapshot={},
            after_snapshot={
                "cart_id": cart.id,
                "citation_numbers": [c.citation_number for c in citations],
                "payment_mode": PaymentMode.ONLINE.value,
                "vendor": VendorName.STRIPE.value,
                "status": cart.status.value,
            },
            metadata={"step": "checkout_started"},
        )

        cart = CartProcessor.add_items_to_cart(
            AddCartItemsRequest(
                cart=cart,
                obligations=filtered_obligations,
                cart_payables=[
                    CartPayable(
                        type="fee",
                        amount=400,
                        status=ObligationStatus.OPEN,
                        label=ObligationLabel.CONVENIENCE_FEE,
                    )
                ],
            ),
            audit_context=checkout_audit_context,
        )

        cart = CartProcessor.checkout_cart(
            cart,
            audit_context=checkout_audit_context,
        )

        checkout_duration_ms = int((time.time() - checkout_start) * 1000)
        AccessLogManager.log_request(
            channel="api",
            request_id=checkout_request_id,
            correlation_id=correlation_id,
            actor_type="user",
            actor_id="demo_user",
            source="online_payment_api",
            method="POST",
            path_or_operation="/payments/checkout",
            target_type="cart",
            target_id=str(cart.id),
            response_status_code=201,
            status="success",
            duration_ms=checkout_duration_ms,
            metadata={
                "citation_numbers": citation_numbers,
                "citation_count": len(citations),
                "obligation_ids": [str(o.id) for o in filtered_obligations],
                "cart_id": str(cart.id),
            },
        )

    except Exception as exc:
        checkout_duration_ms = int((time.time() - checkout_start) * 1000)

        AccessLogManager.log_request(
            channel="api",
            request_id=checkout_request_id,
            correlation_id=None,
            actor_type="user",
            actor_id="demo_user",
            source="online_payment_api",
            method="POST",
            path_or_operation="/payments/checkout",
            target_type="cart",
            response_status_code=500,
            status="failure",
            duration_ms=checkout_duration_ms,
            error_code="CHECKOUT_FAILED",
            error_message=str(exc),
            metadata={"citation_numbers": citation_numbers},
        )

        AuditLogManager.log_event(
            domain="payment",
            action="online_payment.requested",
            entity_type="payment_flow",
            entity_id=f"checkout_request:{checkout_request_id}",
            actor_type="user",
            actor_id="demo_user",
            source="online_payment_api",
            request_id=checkout_request_id,
            correlation_id=None,
            causation_id=f"http_request:{checkout_request_id}",
            status="failure",
            reason=str(exc),
            before_snapshot={},
            after_snapshot={},
            metadata={"step": "checkout_failed", "citation_numbers": citation_numbers},
        )
        raise

    # ------------------------------------------
    # Second API call: submit payment on the cart
    # ------------------------------------------
    submit_request_id = _build_submit_request_id(cart.id)
    submit_start = time.time()

    try:
        submit_audit_context = _build_audit_context(
            actor_type="user",
            actor_id="demo_user",
            source="online_payment_api",
            request_id=submit_request_id,
            correlation_id=correlation_id,
            causation_id=f"http_request:{submit_request_id}",
        )

        AuditLogManager.log_event(
            domain="payment",
            action="online_payment.submitted",
            entity_type="cart",
            entity_id=str(cart.id),
            actor_type="user",
            actor_id="demo_user",
            source="online_payment_api",
            request_id=submit_request_id,
            correlation_id=correlation_id,
            causation_id=f"http_request:{submit_request_id}",
            cart_id=cart.id,
            amount=cart.amount,
            status="success",
            before_snapshot={
                "cart_id": cart.id,
                "status": cart.status.value,
                "amount": cart.amount,
            },
            after_snapshot={
                "cart_id": cart.id,
                "status": cart.status.value,
                "amount": cart.amount,
            },
            metadata={"step": "submit_started"},
        )

        cart = CartProcessor.submit_payment(
            cart,
            audit_context=submit_audit_context,
        )

        submit_duration_ms = int((time.time() - submit_start) * 1000)
        AccessLogManager.log_request(
            channel="api",
            request_id=submit_request_id,
            correlation_id=correlation_id,
            actor_type="user",
            actor_id="demo_user",
            source="online_payment_api",
            method="POST",
            path_or_operation="/payments/submit",
            target_type="cart",
            target_id=str(cart.id),
            response_status_code=202,
            status="success",
            duration_ms=submit_duration_ms,
            metadata={
                "citation_numbers": citation_numbers,
                "cart_id": str(cart.id),
            },
        )

    except Exception as exc:
        submit_duration_ms = int((time.time() - submit_start) * 1000)

        AccessLogManager.log_request(
            channel="api",
            request_id=submit_request_id,
            correlation_id=correlation_id,
            actor_type="user",
            actor_id="demo_user",
            source="online_payment_api",
            method="POST",
            path_or_operation="/payments/submit",
            target_type="cart",
            target_id=str(cart.id),
            response_status_code=500,
            status="failure",
            duration_ms=submit_duration_ms,
            error_code="SUBMIT_PAYMENT_FAILED",
            error_message=str(exc),
            metadata={
                "citation_numbers": citation_numbers,
                "cart_id": str(cart.id),
            },
        )

        AuditLogManager.log_event(
            domain="payment",
            action="online_payment.submitted",
            entity_type="cart",
            entity_id=str(cart.id),
            actor_type="user",
            actor_id="demo_user",
            source="online_payment_api",
            request_id=submit_request_id,
            correlation_id=correlation_id,
            causation_id=f"http_request:{submit_request_id}",
            cart_id=cart.id,
            amount=cart.amount,
            status="failure",
            reason=str(exc),
            before_snapshot={"cart_id": cart.id, "status": cart.status.value},
            after_snapshot={"cart_id": cart.id, "status": cart.status.value},
            metadata={"step": "submit_failed"},
        )
        raise


pay_online(["000331714", "000329181"])
pay_online(["000330575", "000330362"])
