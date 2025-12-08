"""Query preprocessing utilities for biomedical search."""

import re

# Question words and filler words to remove
QUESTION_WORDS: set[str] = {
    # Question starters
    "what",
    "which",
    "how",
    "why",
    "when",
    "where",
    "who",
    "whom",
    # Auxiliary verbs in questions
    "is",
    "are",
    "was",
    "were",
    "do",
    "does",
    "did",
    "can",
    "could",
    "would",
    "should",
    "will",
    "shall",
    "may",
    "might",
    # Filler words in natural questions
    "show",
    "promise",
    "help",
    "believe",
    "think",
    "suggest",
    "possible",
    "potential",
    "effective",
    "useful",
    "good",
    # Articles (remove but less aggressively)
    "the",
    "a",
    "an",
}

# Medical synonym expansions
SYNONYMS: dict[str, list[str]] = {
    "long covid": [
        "long COVID",
        "PASC",
        "post-acute sequelae of SARS-CoV-2",
        "post-COVID syndrome",
        "post-COVID-19 condition",
    ],
    "alzheimer": [
        "Alzheimer's disease",
        "Alzheimer disease",
        "AD",
        "Alzheimer dementia",
    ],
    "parkinson": [
        "Parkinson's disease",
        "Parkinson disease",
        "PD",
    ],
    "diabetes": [
        "diabetes mellitus",
        "type 2 diabetes",
        "T2DM",
        "diabetic",
    ],
    "cancer": [
        "cancer",
        "neoplasm",
        "tumor",
        "malignancy",
        "carcinoma",
    ],
    "heart disease": [
        "cardiovascular disease",
        "CVD",
        "coronary artery disease",
        "heart failure",
    ],
}


def strip_question_words(query: str) -> str:
    """
    Remove question words and filler terms from query.

    Args:
        query: Raw query string

    Returns:
        Query with question words removed
    """
    words = query.lower().split()
    filtered = [w for w in words if w not in QUESTION_WORDS]
    return " ".join(filtered)


def expand_synonyms(query: str) -> str:
    """
    Expand medical terms to include synonyms.

    Args:
        query: Query string

    Returns:
        Query with synonym expansions in OR groups
    """
    result = query.lower()

    for term, expansions in SYNONYMS.items():
        if term in result:
            # Create OR group: ("term1" OR "term2" OR "term3")
            or_group = " OR ".join([f'"{exp}"' for exp in expansions])
            # Case insensitive replacement is tricky with simple replace
            # But we lowercased result already.
            # However, this replaces ALL instances.
            # Also, result is lowercased, so we lose original casing if any.
            # But search engines are usually case-insensitive.
            result = result.replace(term, f"({or_group})")

    return result


def preprocess_query(raw_query: str) -> str:
    """
    Full preprocessing pipeline for PubMed queries.

    Pipeline:
    1. Strip whitespace and punctuation
    2. Remove question words
    3. Expand medical synonyms

    Args:
        raw_query: Natural language query from user

    Returns:
        Optimized query for PubMed
    """
    if not raw_query or not raw_query.strip():
        return ""

    # Remove question marks and extra whitespace
    query = raw_query.replace("?", "").strip()
    query = re.sub(r"\s+", " ", query)

    # Strip question words
    query = strip_question_words(query)

    # Expand synonyms
    query = expand_synonyms(query)

    return query.strip()


def preprocess_web_query(raw_query: str) -> str:
    """
    Simplified preprocessing pipeline for web search engines (Serper, DuckDuckGo, etc.).

    Web search engines work better with natural language queries rather than
    complex boolean syntax. This function:
    1. Strips whitespace and punctuation
    2. Removes question words (less aggressively)
    3. Removes complex boolean syntax (OR groups, parentheses)
    4. Uses primary synonym terms instead of expanding to OR groups

    Args:
        raw_query: Natural language query from user

    Returns:
        Simplified query optimized for web search engines
    """
    if not raw_query or not raw_query.strip():
        return ""

    # Remove question marks and extra whitespace
    query = raw_query.replace("?", "").strip()
    query = re.sub(r"\s+", " ", query)

    # Remove complex boolean syntax that might have been added
    # Remove OR groups like: ("term1" OR "term2" OR "term3")
    query = re.sub(r'\([^)]*OR[^)]*\)', '', query, flags=re.IGNORECASE)
    # Remove standalone OR statements
    query = re.sub(r'\s+OR\s+', ' ', query, flags=re.IGNORECASE)
    # Remove extra parentheses
    query = re.sub(r'[()]', '', query)
    # Remove extra quotes that might be left
    query = re.sub(r'"([^"]*)"', r'\1', query)
    # Clean up multiple spaces
    query = re.sub(r'\s+', ' ', query)

    # Strip question words (less aggressively - keep important context words)
    # Only remove very common question starters
    minimal_question_words = {"what", "which", "how", "why", "when", "where", "who"}
    words = query.split()
    filtered = [w for w in words if w.lower() not in minimal_question_words]
    query = " ".join(filtered)

    # Replace known medical terms with their primary/common form
    # Use the first synonym (most common) instead of OR groups
    query_lower = query.lower()
    for term, expansions in SYNONYMS.items():
        if term in query_lower:
            # Use the first expansion (usually the most common term)
            primary_term = expansions[0] if expansions else term
            # Replace case-insensitively, preserving original case where possible
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            query = pattern.sub(primary_term, query)

    return query.strip()