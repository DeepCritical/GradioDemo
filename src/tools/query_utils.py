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
