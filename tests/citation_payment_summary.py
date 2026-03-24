from processors.citation_manager import CitationManager

citations = CitationManager.read_citations()
for citation in citations:
    CitationManager.get_citation_obligation_result(
        citation_number=citation.citation_number
    )
