from core.models.models import (
    ObligationCreationRequest,
    ObligationLabel,
    ObligationOwnerType,
    ObligationStatus,
)
from processors.obligation_processor import ObligationProcessor

obligation = ObligationProcessor.add_payable(
    ObligationCreationRequest(
        type="test_fee",
        amount=1000,
        owner_type=ObligationOwnerType.CITATION,
        owner_id="000329019",
        status=ObligationStatus.OPEN,
        label=ObligationLabel.LATE_FEE,
    )
)

ObligationProcessor.waive_obligation(obligation=obligation)
