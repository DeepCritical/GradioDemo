"""Europe PMC search tool - replaces BioRxiv."""

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.exceptions import SearchError
from src.utils.models import Citation, Evidence


class EuropePMCTool:
    """
    Search Europe PMC for papers and preprints.

    Europe PMC indexes:
    - PubMed/MEDLINE articles
    - PMC full-text articles
    - Preprints from bioRxiv, medRxiv, ChemRxiv, etc.
    - Patents and clinical guidelines

    API Docs: https://europepmc.org/RestfulWebService
    """

    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    @property
    def name(self) -> str:
        return "europepmc"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def search(self, query: str, max_results: int = 10) -> list[Evidence]:
        """
        Search Europe PMC for papers matching query.

        Args:
            query: Search keywords
            max_results: Maximum results to return

        Returns:
            List of Evidence objects
        """
        params: dict[str, str | int] = {
            "query": query,
            "resultType": "core",
            "pageSize": min(max_results, 100),
            "format": "json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()

                data = response.json()
                results = data.get("resultList", {}).get("result", [])

                return [self._to_evidence(r) for r in results[:max_results]]

            except httpx.HTTPStatusError as e:
                raise SearchError(f"Europe PMC API error: {e}") from e
            except httpx.RequestError as e:
                raise SearchError(f"Europe PMC connection failed: {e}") from e

    def _to_evidence(self, result: dict[str, Any]) -> Evidence:
        """Convert Europe PMC result to Evidence."""
        title = result.get("title", "Untitled")
        abstract = result.get("abstractText", "No abstract available.")
        doi = result.get("doi", "")
        pub_year = result.get("pubYear", "Unknown")

        # Get authors
        author_list = result.get("authorList", {}).get("author", [])
        authors = [a.get("fullName", "") for a in author_list[:5] if a.get("fullName")]

        # Check if preprint
        pub_types = result.get("pubTypeList", {}).get("pubType", [])
        is_preprint = "Preprint" in pub_types
        source_db = result.get("source", "europepmc")

        # Build content
        preprint_marker = "[PREPRINT - Not peer-reviewed] " if is_preprint else ""
        content = f"{preprint_marker}{abstract[:1800]}"

        # Build URL
        if doi:
            url = f"https://doi.org/{doi}"
        elif result.get("pmid"):
            url = f"https://pubmed.ncbi.nlm.nih.gov/{result['pmid']}/"
        else:
            url = f"https://europepmc.org/article/{source_db}/{result.get('id', '')}"

        return Evidence(
            content=content[:2000],
            citation=Citation(
                source="preprint" if is_preprint else "europepmc",
                title=title[:500],
                url=url,
                date=str(pub_year),
                authors=authors,
            ),
            relevance=0.75 if is_preprint else 0.9,
        )
