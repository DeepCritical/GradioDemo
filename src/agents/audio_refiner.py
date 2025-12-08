"""Audio Refiner Agent - Cleans markdown reports for TTS audio clarity.

This agent transforms markdown-formatted research reports into clean,
audio-friendly plain text suitable for text-to-speech synthesis.
"""

import re

import structlog
from pydantic_ai import Agent

from src.utils.llm_factory import get_pydantic_ai_model

logger = structlog.get_logger(__name__)


class AudioRefiner:
    """Refines markdown reports for optimal TTS audio output.

    Handles common formatting issues that make text difficult to listen to:
    - Markdown syntax (headers, bold, italic, links)
    - Citations and reference markers
    - Roman numerals in medical contexts
    - Multiple References sections
    - Special characters and formatting artifacts
    """

    # Roman numeral to integer mapping
    ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

    # Number to word mapping (1-20, common in medical literature)
    NUMBER_TO_WORD = {
        1: "One",
        2: "Two",
        3: "Three",
        4: "Four",
        5: "Five",
        6: "Six",
        7: "Seven",
        8: "Eight",
        9: "Nine",
        10: "Ten",
        11: "Eleven",
        12: "Twelve",
        13: "Thirteen",
        14: "Fourteen",
        15: "Fifteen",
        16: "Sixteen",
        17: "Seventeen",
        18: "Eighteen",
        19: "Nineteen",
        20: "Twenty",
    }

    async def refine_for_audio(self, markdown_text: str, use_llm_polish: bool = False) -> str:
        """Transform markdown report into audio-friendly plain text.

        Args:
            markdown_text: Markdown-formatted research report
            use_llm_polish: If True, apply LLM-based final polish (optional)

        Returns:
            Clean plain text optimized for TTS audio
        """
        logger.info("Refining report for audio output", use_llm_polish=use_llm_polish)

        text = markdown_text

        # Step 1: Remove References sections first (before other processing)
        text = self._remove_references_sections(text)

        # Step 2: Remove markdown formatting
        text = self._remove_markdown_syntax(text)

        # Step 3: Convert roman numerals to words
        text = self._convert_roman_numerals(text)

        # Step 4: Remove citations
        text = self._remove_citations(text)

        # Step 5: Clean up special characters and artifacts
        text = self._clean_special_characters(text)

        # Step 6: Normalize whitespace
        text = self._normalize_whitespace(text)

        # Step 7 (Optional): LLM polish for edge cases
        if use_llm_polish:
            text = await self._llm_polish(text)

        logger.info(
            "Audio refinement complete",
            original_length=len(markdown_text),
            refined_length=len(text),
            llm_polish_applied=use_llm_polish,
        )

        return text.strip()

    def _remove_references_sections(self, text: str) -> str:
        """Remove References sections while preserving other content.

        Removes the References section and its content until the next section
        heading or end of document. Handles multiple References sections.

        Matches various References heading formats:
        - # References
        - ## References
        - **References:**
        - **Additional References:**
        - References: (plain text)
        """
        # Pattern to match References section heading (case-insensitive)
        # Matches: markdown headers (# References), bold (**References:**), or plain text (References:)
        references_pattern = r"\n(?:#+\s*References?:?\s*\n|\*\*\s*(?:Additional\s+)?References?:?\s*\*\*\s*\n|References?:?\s*\n)"

        # Find all References sections
        while True:
            match = re.search(references_pattern, text, re.IGNORECASE)
            if not match:
                break

            # Find the start of the References section
            section_start = match.start()

            # Find the next section (markdown header or bold heading) or end of document
            # Match: "# Header", "## Header", or "**Header**"
            next_section_patterns = [
                r"\n#+\s+\w+",  # Markdown headers (# Section, ## Section)
                r"\n\*\*[A-Z][^*]+\*\*",  # Bold headings (**Section Name**)
            ]

            remaining_text = text[match.end() :]
            next_section_match = None

            # Try all patterns and find the earliest match
            earliest_match = None
            for pattern in next_section_patterns:
                m = re.search(pattern, remaining_text)
                if m and (earliest_match is None or m.start() < earliest_match.start()):
                    earliest_match = m

            next_section_match = earliest_match

            if next_section_match:
                # Remove from References heading to next section
                section_end = match.end() + next_section_match.start()
            else:
                # No next section - remove to end of document
                section_end = len(text)

            # Remove the References section
            text = text[:section_start] + text[section_end:]
            logger.debug("Removed References section", removed_chars=section_end - section_start)

        return text

    def _remove_markdown_syntax(self, text: str) -> str:
        """Remove markdown formatting syntax."""

        # Headers (# ## ###)
        text = re.sub(r"^\s*#+\s+", "", text, flags=re.MULTILINE)

        # Bold (**text** or __text__)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)

        # Italic (*text* or _text_)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)

        # Links [text](url) → text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Inline code `code` → code
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # Strikethrough ~~text~~
        text = re.sub(r"~~([^~]+)~~", r"\1", text)

        # Blockquotes (> text)
        text = re.sub(r"^\s*>\s+", "", text, flags=re.MULTILINE)

        # Horizontal rules (---, ***, ___)
        text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

        # List markers (-, *, 1., 2.)
        text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

        return text

    def _roman_to_int(self, roman: str) -> int | None:
        """Convert roman numeral string to integer.

        Args:
            roman: Roman numeral string (e.g., 'IV', 'XII')

        Returns:
            Integer value, or None if invalid roman numeral
        """
        roman = roman.upper()
        result = 0
        prev_value = 0

        for char in reversed(roman):
            if char not in self.ROMAN_VALUES:
                return None

            value = self.ROMAN_VALUES[char]

            # Subtractive notation (IV = 4, IX = 9)
            if value < prev_value:
                result -= value
            else:
                result += value

            prev_value = value

        return result

    def _int_to_word(self, num: int) -> str:
        """Convert integer to word representation.

        Args:
            num: Integer to convert (1-20 supported)

        Returns:
            Word representation (e.g., 'One', 'Twelve')
        """
        if num in self.NUMBER_TO_WORD:
            return self.NUMBER_TO_WORD[num]
        else:
            # For numbers > 20, just return the digit
            return str(num)

    def _convert_roman_numerals(self, text: str) -> str:
        """Convert roman numerals to words for better TTS pronunciation.

        Handles patterns like:
        - Phase I, Phase II, Phase III
        - Trial I, Trial II
        - Type I, Type II
        - Stage I, Stage II
        - Standalone I, II, III (with word boundaries)
        """

        def replace_roman(match: re.Match[str]) -> str:
            """Callback to replace matched roman numeral."""
            prefix = match.group(1)  # Word before roman numeral (if any)
            roman = match.group(2)  # The roman numeral

            # Convert to integer
            num = self._roman_to_int(roman)
            if num is None:
                return match.group(0)  # Return original if invalid

            # Convert to word
            word = self._int_to_word(num)

            # Return with prefix if present
            if prefix:
                return f"{prefix} {word}"
            else:
                return word

        # Pattern: Optional word + space + roman numeral
        # Matches: "Phase I", "Trial II", standalone "I", "II"
        # Uses word boundaries to avoid matching "I" in "INVALID"
        pattern = r"\b(Phase|Trial|Type|Stage|Class|Group|Arm|Cohort)?\s*([IVXLCDM]+)\b"

        text = re.sub(pattern, replace_roman, text)

        return text

    def _remove_citations(self, text: str) -> str:
        """Remove citation markers and references."""

        # Numbered citations [1], [2], [1,2], [1-3]
        text = re.sub(r"\[\d+(?:[-,]\d+)*\]", "", text)

        # Author citations (Smith et al., 2023) or (Smith et al. 2023)
        text = re.sub(r"\([A-Z][a-z]+\s+et\s+al\.?,?\s+\d{4}\)", "", text)

        # Simple year citations (2023)
        text = re.sub(r"\(\d{4}\)", "", text)

        # Author-year (Smith, 2023)
        text = re.sub(r"\([A-Z][a-z]+,?\s+\d{4}\)", "", text)

        # Footnote markers (¹, ², ³)
        text = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹⁰]+", "", text)

        return text

    def _clean_special_characters(self, text: str) -> str:
        """Clean up special characters and formatting artifacts."""

        # Replace em dashes with regular dashes
        text = text.replace("\u2014", "-")  # em dash
        text = text.replace("\u2013", "-")  # en dash

        # Replace smart quotes with regular quotes
        text = text.replace("\u201c", '"')  # left double quote
        text = text.replace("\u201d", '"')  # right double quote
        text = text.replace("\u2018", "'")  # left single quote
        text = text.replace("\u2019", "'")  # right single quote

        # Remove excessive punctuation (!!!, ???)
        text = re.sub(r"([!?]){2,}", r"\1", text)

        # Remove asterisks used for footnotes
        text = re.sub(r"\*+", "", text)

        # Remove hash symbols (from headers)
        text = text.replace("#", "")

        # Remove excessive dots (...)
        text = re.sub(r"\.{4,}", "...", text)

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace for clean audio output."""

        # Replace multiple spaces with single space
        text = re.sub(r" {2,}", " ", text)

        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove trailing/leading whitespace from lines
        text = "\n".join(line.strip() for line in text.split("\n"))

        # Remove empty lines at start/end
        text = text.strip()

        return text

    async def _llm_polish(self, text: str) -> str:
        """Apply LLM-based final polish to catch edge cases.

        This is a lightweight pass that removes any remaining formatting
        artifacts the rule-based methods might have missed.

        Args:
            text: Pre-cleaned text from rule-based methods

        Returns:
            Final polished text ready for TTS
        """
        try:
            # Create a simple agent for text cleanup
            model = get_pydantic_ai_model()
            polish_agent = Agent(
                model=model,
                system_prompt=(
                    "You are a text cleanup assistant. Your ONLY job is to remove "
                    "any remaining formatting artifacts (markdown, citations, special "
                    "characters) that make text unsuitable for text-to-speech audio. "
                    "DO NOT rewrite, improve, or change the content. "
                    "DO NOT add explanations. "
                    "ONLY output the cleaned text."
                ),
            )

            # Run asynchronously
            result = await polish_agent.run(
                f"Clean this text for audio (remove any formatting artifacts):\n\n{text}"
            )

            polished_text = result.output.strip()

            logger.info(
                "llm_polish_applied", original_length=len(text), polished_length=len(polished_text)
            )

            return polished_text

        except Exception as e:
            logger.warning(
                "llm_polish_failed", error=str(e), message="Falling back to rule-based output"
            )
            # Graceful fallback: return original text if LLM fails
            return text


# Singleton instance for easy import
audio_refiner = AudioRefiner()


async def refine_text_for_audio(markdown_text: str, use_llm_polish: bool = False) -> str:
    """Convenience function to refine markdown text for audio.

    Args:
        markdown_text: Markdown-formatted text
        use_llm_polish: If True, apply LLM-based final polish (optional)

    Returns:
        Audio-friendly plain text
    """
    return await audio_refiner.refine_for_audio(markdown_text, use_llm_polish=use_llm_polish)
