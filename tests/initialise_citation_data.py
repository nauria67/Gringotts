import csv
import json

from core.models.models import (
    Citation,
    Obligation,
    ObligationCreationRequest,
    ObligationLabel,
    ObligationStatus,
)
from processors.citation_manager import CitationManager
from processors.obligation_processor import ObligationProcessor

# Initialize the processor
processor = ObligationProcessor()

citations = CitationManager.read_citations()

# Create obligations from citations
obligations = []
for citation in citations:
    request = ObligationCreationRequest(
        type="citation",
        amount=citation.amount_due,
        owner_type="citation",
        owner_id=citation.citation_number,
        status=ObligationStatus.OPEN,
        label=ObligationLabel.CITATION_FEE,
    )
    processor.add_payable(request)
