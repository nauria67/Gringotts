from typing import List

from core.models.models import Obligation, ObligationCreationRequest
from processors.obligation_processor import ObligationProcessor


class ObligationService:
    def __init__(self, repo):
        pass

    def create(self, request: ObligationCreationRequest) -> Obligation:
        Obligation.from_dict(
            {
                "owner_id": request.owner_id,
                "owner_type": request.owner_type,
                "fee_type": request.type,
                "amount": request.amount,
                "status": request.status,
            }
        )
        return
