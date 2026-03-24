import csv

from core.models.models import Citation
from processors.obligation_processor import ObligationProcessor


class CitationManager:

    @staticmethod
    def read_citations():
        """Read citations from the CSV file."""
        citations = []
        with open("/Users/obvio/Desktop/gringotts/data/citations.csv", "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                citations.append(
                    Citation(
                        citation_number=row["citation_number"],
                        ticket_amount=row["citation_due_amount"],
                        amount_due=row["citation_due_amount"],
                        amount_paid=row["citation_amount_paid"],
                        payment_status=row["payment_status"],
                        citation_stage=row["citation_stage"],
                        citation_status=row["citation_status"],
                        payment_date=row.get("latest_payment_date"),
                        source=row["payment_source"],
                    )
                )
        return citations

    @staticmethod
    def get_citation_by_number(citation_number: str) -> Citation:
        """Get a citation by its citation number."""
        citations = CitationManager.read_citations()
        for citation in citations:
            if citation.citation_number == citation_number:
                return citation
        raise ValueError(f"Citation with number {citation_number} not found.")

    @staticmethod
    def get_citation_obligation_result(citation_number: str):
        citation = CitationManager.get_citation_by_number(citation_number)
        payment_summary = ObligationProcessor.get_owner_payment_summary(
            owner_id=citation.citation_number,
            owner_type="citation",
        )
        print(f"Citation: {citation}")
        print(f"Payment Summary: {payment_summary}")
        print(f"Payment Summary: {payment_summary}")
