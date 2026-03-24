import csv
from typing import List

from datamodel.models import Obligation

from .repository import ObligationRepository


class CSVObligationRepository(ObligationRepository):
    """CSV-based implementation of the ObligationRepository."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def save(self, obligation: Obligation) -> None:
        """Save an obligation to the CSV file."""
        with open(self.file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                obligation.id,
                obligation.owner_id,
                obligation.owner_type,
                obligation.fee_type,
                obligation.name,
                obligation.status,
                obligation.locked_by,
            ])

    def find_all(self) -> List[Obligation]:
        """Retrieve all obligations from the CSV file."""
        obligations = []
        with open(self.file_path, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                obligations.append(Obligation(
                    id=row['id'],
                    owner_id=row['owner_id'],
                    owner_type=row['owner_type'],
                    fee_type=row['fee_type'],
                    name=row['name'],
                    status=row['status'],
                    locked_by=row['locked_by'],
                ))
        return obligations

    def find_by_id(self, obligation_id: str) -> Obligation:
        """Find an obligation by its ID in the CSV file."""
        obligations = self.find_all()
        for obligation in obligations:
            if obligation.id == obligation_id:
                return obligation
        raise ValueError(f"Obligation with ID {obligation_id} not found.")

    def delete(self, obligation_id: str) -> None:
        """Delete an obligation by its ID from the CSV file."""
        obligations = self.find_all()
        obligations = [o for o in obligations if o.id != obligation_id]
        with open(self.file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['id', 'owner_id', 'owner_type', 'fee_type', 'name', 'status', 'locked_by'])
            for obligation in obligations:
                writer.writerow([
                    obligation.id,
                    obligation.owner_id,
                    obligation.owner_type,
                    obligation.fee_type,
                    obligation.name,
                    obligation.status,
                    obligation.locked_by,
                ])
                    obligation.status,
                    obligation.locked_by,
                ])
