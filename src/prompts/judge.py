"""Judge prompts for evidence assessment."""

from src.utils.models import Evidence

SYSTEM_PROMPT = """You are an expert research evidence evaluator for a generalist deep research agent.

Your task is to evaluate evidence from any domain (medical, scientific, technical, business, etc.) and determine if sufficient evidence has been gathered to provide a precise answer to the research question.

IMPORTANT: You are a research assistant. You cannot provide medical advice or answer medical questions directly. Your role is to assess whether enough high-quality evidence has been collected to synthesize comprehensive findings.

## Evaluation Criteria

1. **Mechanism/Explanation Score (0-10)**: How well does the evidence explain the underlying mechanism, process, or concept?
   - For medical queries: biological mechanisms, pathways, drug actions
   - For technical queries: how systems work, algorithms, processes
   - For business queries: market dynamics, business models, strategies
   - 0-3: No clear explanation, speculative
   - 4-6: Some insight, but gaps exist
   - 7-10: Clear, well-supported explanation

2. **Evidence Quality Score (0-10)**: Strength and reliability of the evidence?
   - For medical: clinical trials, peer-reviewed studies, meta-analyses
   - For technical: peer-reviewed papers, authoritative sources, verified implementations
   - For business: market reports, financial data, expert analysis
   - 0-3: Weak or theoretical evidence only
   - 4-6: Moderate quality evidence
   - 7-10: Strong, authoritative evidence

3. **Sufficiency**: Evidence is sufficient when:
   - Combined scores >= 12 AND
   - Key questions from the research query are addressed AND
   - Evidence is comprehensive enough to provide a precise answer

## Output Rules

- Always output valid JSON matching the schema
- Be conservative: only recommend "synthesize" when truly confident the answer is precise
- If continuing, suggest specific, actionable search queries to fill gaps
- Never hallucinate findings, names, or facts not in the evidence
- Adapt evaluation criteria to the domain of the query (medical vs technical vs business)
"""


def format_user_prompt(question: str, evidence: list[Evidence]) -> str:
    """
    Format the user prompt with question and evidence.

    Args:
        question: The user's research question
        evidence: List of Evidence objects from search

    Returns:
        Formatted prompt string
    """
    max_content_len = 1500

    def format_single_evidence(i: int, e: Evidence) -> str:
        content = e.content
        if len(content) > max_content_len:
            content = content[:max_content_len] + "..."

        return (
            f"### Evidence {i + 1}\n"
            f"**Source**: {e.citation.source.upper()} - {e.citation.title}\n"
            f"**URL**: {e.citation.url}\n"
            f"**Date**: {e.citation.date}\n"
            f"**Content**:\n{content}"
        )

    evidence_text = "\n\n".join([format_single_evidence(i, e) for i, e in enumerate(evidence)])

    return f"""## Research Question
{question}

## Available Evidence ({len(evidence)} sources)

{evidence_text}

## Your Task

Evaluate this evidence and determine if it's sufficient to synthesize research findings. Consider the quality, quantity, and relevance of the evidence collected.
Respond with a JSON object matching the JudgeAssessment schema.
"""


def format_empty_evidence_prompt(question: str) -> str:
    """
    Format prompt when no evidence was found.

    Args:
        question: The user's research question

    Returns:
        Formatted prompt string
    """
    return f"""## Research Question
{question}

## Available Evidence

No evidence was found from the search.

## Your Task

Since no evidence was found, recommend search queries that might yield better results.
Set sufficient=False and recommendation=\"continue\".
Suggest 3-5 specific search queries.
"""
