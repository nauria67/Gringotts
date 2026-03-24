from typing import List

from datamodel.models import Obligation


class ObligationRepository:
    """Base repository for managing obligations."""

    def save(self, obligation: Obligation) -> None:
        """Save an obligation to the repository."""
        raise NotImplementedError("Subclasses must implement this method.")

    def find_all(self) -> List[Obligation]:
        """Retrieve all obligations from the repository."""
        raise NotImplementedError("Subclasses must implement this method.")

    def find_by_id(self, obligation_id: str) -> Obligation:
        """Find an obligation by its ID."""
        raise NotImplementedError("Subclasses must implement this method.")

    def delete(self, obligation_id: str) -> None:
        """Delete an obligation by its ID."""
        raise NotImplementedError("Subclasses must implement this method.")
