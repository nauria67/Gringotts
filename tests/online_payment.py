## se;ect 2 payment pending citations from citations csv. Identify obligations against those citations
import csv

from core.models.models import (
    AddCartItemsRequest,
    CartCreationRequest,
    CartPayable,
    CartStatus,
    Citation,
    Obligation,
    ObligationFilterRequest,
    ObligationLabel,
    ObligationStatus,
    PaymentMode,
    VendorName,
)
from processors.cart_processor import CartProcessor
from processors.obligation_processor import ObligationProcessor

# Initialize the processor


# Read citations from data/citations.csv
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
    # Filter for payment pending citations
    payment_pending_citations = [
        c
        for c in citations
        if c.citation_stage == "payment" and c.citation_status == "pending"
    ]
    # find obligations from the obligations csv for the payment pending citations
    obligations = []
    obligations = ObligationProcessor.read_obligations_from_csv()

    return payment_pending_citations, obligations


def pay_online(citation_numbers):

    citations, obligations = fetch_data()
    citations = [c for c in citations if c.citation_number in citation_numbers]
    obligation_processor = ObligationProcessor()

    filtered_obligations = []
    for citation in citations:
        filtered_obligations_temp = obligation_processor.filter_obligations(
            obligations,
            ObligationFilterRequest(
                owner_type="citation",
                owner_id=citations.citation_number,
                status=ObligationStatus.OPEN,
            ),
        )
        filtered_obligations.extend(filtered_obligations_temp)

    cart_processor = CartProcessor()
    cart = cart_processor.create_cart(
        CartCreationRequest(
            status=CartStatus.DRAFT,
            vendor=VendorName.STRIPE,
            payment_mode=PaymentMode.ONLINE,
        )
    )
    cart = cart_processor.add_items_to_cart(
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
    )
    cart_processor.checkout_cart(cart)

    cart_processor.submit_payment(cart)


def pay_online(citation_numbers):

    ## first api call to checkout cart

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

    cart_processor = CartProcessor()
    cart = cart_processor.create_cart(
        CartCreationRequest(
            status=CartStatus.DRAFT,
            vendor=VendorName.STRIPE,
            payment_mode=PaymentMode.ONLINE,
        )
    )
    cart = cart_processor.add_items_to_cart(
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
    )
    cart_processor.checkout_cart(cart)

    ## second api call to submit payment for the checked out cart

    cart_processor.submit_payment(cart)


pay_online(["000331714", "000329181"])
pay_online(["000330575", "000330362"])
