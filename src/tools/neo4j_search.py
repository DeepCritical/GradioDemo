"""Neo4j knowledge graph search tool."""

import structlog

from src.services.neo4j_service import get_neo4j_service
from src.utils.models import Citation, Evidence

logger = structlog.get_logger()


class Neo4jSearchTool:
    """Search Neo4j knowledge graph for papers."""

    def __init__(self) -> None:
        self.name = "neo4j"  # ✅ Definir explícitamente

    async def search(self, query: str, max_results: int = 10) -> list[Evidence]:
        """Search Neo4j for papers about diseases in the query."""
        try:
            service = get_neo4j_service()
            if not service:
                logger.warning("Neo4j service not available")
                return []

            # Extract disease name from query
            disease = query
            if "for" in query.lower():
                disease = query.split("for")[-1].strip().rstrip("?")

            # Query Neo4j
            if not service.driver:
                logger.warning("Neo4j driver not available")
                return []
            with service.driver.session(database=service.database) as session:
                result = session.run(
                    """
                    MATCH (p:Paper)-[:ABOUT]->(d:Disease)
                    WHERE d.name CONTAINS $disease
                    RETURN p.title as title, p.abstract as abstract, 
                           p.url as url, p.source as source
                    ORDER BY p.updated_at DESC
                    LIMIT $max_results
                """,
                    disease=disease,
                    max_results=max_results,
                )

                records = list(result)

            results = []
            for record in records:
                citation = Citation(
                    source="neo4j",
                    title=record["title"] or "Untitled",
                    url=record["url"] or "",
                    date="",
                    authors=[],
                )

                evidence = Evidence(
                    content=record["abstract"] or record["title"] or "",
                    citation=citation,
                    relevance=1.0,
                    metadata={"from_kb": True, "original_source": record["source"]},
                )
                results.append(evidence)

            logger.info(f"📊 Neo4j returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Neo4j search failed: {e}")
            return []
