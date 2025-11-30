# Prompt Engineering & Citation Validation

This document outlines prompt engineering guidelines and citation validation rules.

## Judge Prompts

- System prompt in `src/prompts/judge.py`
- Format evidence with truncation (1500 chars per item)
- Handle empty evidence case separately
- Always request structured JSON output
- Use `format_user_prompt()` and `format_empty_evidence_prompt()` helpers

## Hypothesis Prompts

- Use diverse evidence selection (MMR algorithm)
- Sentence-aware truncation (`truncate_at_sentence()`)
- Format: Drug → Target → Pathway → Effect
- System prompt emphasizes mechanistic reasoning
- Use `format_hypothesis_prompt()` with embeddings for diversity

## Report Prompts

- Include full citation details for validation
- Use diverse evidence selection (n=20)
- **CRITICAL**: Emphasize citation validation rules
- Format hypotheses with support/contradiction counts
- System prompt includes explicit JSON structure requirements

## Citation Validation

- **ALWAYS** validate references before returning reports
- Use `validate_references()` from `src/utils/citation_validator.py`
- Remove hallucinated citations (URLs not in evidence)
- Log warnings for removed citations
- Never trust LLM-generated citations without validation

## Citation Validation Rules

1. Every reference URL must EXACTLY match a provided evidence URL
2. Do NOT invent, fabricate, or hallucinate any references
3. Do NOT modify paper titles, authors, dates, or URLs
4. If unsure about a citation, OMIT it rather than guess
5. Copy URLs exactly as provided - do not create similar-looking URLs

## Evidence Selection

- Use `select_diverse_evidence()` for MMR-based selection
- Balance relevance vs diversity (lambda=0.7 default)
- Sentence-aware truncation preserves meaning
- Limit evidence per prompt to avoid context overflow

## See Also

- [Code Quality](code-quality.md) - Code quality guidelines
- [Error Handling](error-handling.md) - Error handling guidelines















