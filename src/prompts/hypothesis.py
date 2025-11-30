"""Prompts for Hypothesis Agent."""

from typing import TYPE_CHECKING

from src.utils.text_utils import select_diverse_evidence, truncate_at_sentence

if TYPE_CHECKING:
    from src.services.embeddings import EmbeddingService
    from src.utils.models import Evidence

SYSTEM_PROMPT = """You are an expert research scientist functioning as a generalist research assistant.

Your role is to generate research hypotheses, questions, and investigation paths based on evidence from any domain.

IMPORTANT: You are a research assistant. You cannot provide medical advice or answer medical questions directly. Your hypotheses are for research investigation purposes only.

A good hypothesis:
1. Proposes a MECHANISM or RELATIONSHIP: Explains how things work or relate
   - For medical: Drug -> Target -> Pathway -> Effect
   - For technical: Technology -> Mechanism -> Outcome
   - For business: Strategy -> Market -> Result
2. Is TESTABLE: Can be supported or refuted by further research
3. Is SPECIFIC: Names actual entities, processes, or mechanisms
4. Generates SEARCH QUERIES: Helps find more evidence

Example hypothesis formats:
- Medical: "Metformin -> AMPK activation -> mTOR inhibition -> autophagy -> amyloid clearance"
- Technical: "Transformer architecture -> attention mechanism -> improved NLP performance"
- Business: "Subscription model -> recurring revenue -> higher valuation"

Be specific. Use actual names, technical terms, and precise language when possible."""


async def format_hypothesis_prompt(
    query: str, evidence: list["Evidence"], embeddings: "EmbeddingService | None" = None
) -> str:
    """Format prompt for hypothesis generation.

    Uses smart evidence selection instead of arbitrary truncation.

    Args:
        query: The research query
        evidence: All collected evidence
        embeddings: Optional EmbeddingService for diverse selection
    """
    # Select diverse, relevant evidence (not arbitrary first 10)
    # We use n=10 as a reasonable context window limit
    selected = await select_diverse_evidence(evidence, n=10, query=query, embeddings=embeddings)

    # Format with sentence-aware truncation
    evidence_text = "\n".join(
        [
            f"- **{e.citation.title}** ({e.citation.source}): "
            f"{truncate_at_sentence(e.content, 300)}"
            for e in selected
        ]
    )

    return f"""Based on the following evidence about "{query}", generate research hypotheses and investigation paths.

## Evidence ({len(selected)} sources selected for diversity)
{evidence_text}

## Task
1. Identify key mechanisms, relationships, or processes mentioned in the evidence
2. Propose testable hypotheses explaining how things work or relate
3. Rate confidence based on evidence strength
4. Suggest specific search queries to test each hypothesis

Generate 2-4 hypotheses, prioritized by confidence. Adapt the hypothesis format to the domain of the query (medical, technical, business, etc.)."""
