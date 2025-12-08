"""Unit tests for AudioRefiner agent."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.agents.audio_refiner import AudioRefiner, refine_text_for_audio


class TestAudioRefiner:
    """Test suite for AudioRefiner functionality."""

    @pytest.fixture
    def refiner(self):
        """Create AudioRefiner instance."""
        return AudioRefiner()

    def test_remove_markdown_headers(self, refiner):
        """Test removal of markdown headers."""
        text = """# Main Title
## Subtitle
### Section
Content here"""
        result = refiner._remove_markdown_syntax(text)
        assert "#" not in result
        assert "Main Title" in result
        assert "Subtitle" in result

    def test_remove_bold_italic(self, refiner):
        """Test removal of bold and italic formatting."""
        text = "**Bold text** and *italic text* and __another bold__"
        result = refiner._remove_markdown_syntax(text)
        assert "**" not in result
        assert "*" not in result
        assert "__" not in result
        assert "Bold text" in result
        assert "italic text" in result

    def test_remove_links(self, refiner):
        """Test removal of markdown links."""
        text = "Check [this link](https://example.com) for details"
        result = refiner._remove_markdown_syntax(text)
        assert "[" not in result
        assert "]" not in result
        assert "https://" not in result
        assert "this link" in result

    def test_remove_citations_numbered(self, refiner):
        """Test removal of numbered citations."""
        text = "Research shows [1] that metformin [2,3] works [4-6]."
        result = refiner._remove_citations(text)
        assert "[1]" not in result
        assert "[2,3]" not in result
        assert "[4-6]" not in result
        assert "Research shows" in result

    def test_remove_citations_author_year(self, refiner):
        """Test removal of author-year citations."""
        text = "Studies (Smith et al., 2023) and (Jones, 2022) confirm this."
        result = refiner._remove_citations(text)
        assert "(Smith et al., 2023)" not in result
        assert "(Jones, 2022)" not in result
        assert "Studies" in result
        assert "confirm this" in result

    def test_remove_first_references_section(self, refiner):
        """Test that References sections are removed while preserving other content."""
        text = """Main content here.

# References
[1] First reference
[2] Second reference

# More Content
This should remain.

## References
This second References should also be removed."""

        result = refiner._remove_references_sections(text)
        assert "Main content here" in result
        assert "References" not in result
        assert "First reference" not in result
        assert "More Content" in result  # Content after References should be preserved
        assert "This should remain" in result
        assert "second References should also be removed" not in result  # Second References section removed

    def test_roman_to_int_conversion(self, refiner):
        """Test roman numeral to integer conversion."""
        assert refiner._roman_to_int("I") == 1
        assert refiner._roman_to_int("II") == 2
        assert refiner._roman_to_int("III") == 3
        assert refiner._roman_to_int("IV") == 4
        assert refiner._roman_to_int("V") == 5
        assert refiner._roman_to_int("IX") == 9
        assert refiner._roman_to_int("X") == 10
        assert refiner._roman_to_int("XII") == 12
        assert refiner._roman_to_int("XX") == 20

    def test_int_to_word_conversion(self, refiner):
        """Test integer to word conversion."""
        assert refiner._int_to_word(1) == "One"
        assert refiner._int_to_word(2) == "Two"
        assert refiner._int_to_word(3) == "Three"
        assert refiner._int_to_word(10) == "Ten"
        assert refiner._int_to_word(20) == "Twenty"
        assert refiner._int_to_word(25) == "25"  # Falls back to digit

    def test_convert_roman_numerals_with_context(self, refiner):
        """Test roman numeral conversion with context words."""
        test_cases = [
            ("Phase I trial", "Phase One trial"),
            ("Phase II study", "Phase Two study"),
            ("Phase III data", "Phase Three data"),
            ("Type I diabetes", "Type One diabetes"),
            ("Type II error", "Type Two error"),
            ("Stage IV cancer", "Stage Four cancer"),
            ("Trial I results", "Trial One results"),
        ]

        for input_text, expected in test_cases:
            result = refiner._convert_roman_numerals(input_text)
            assert expected in result, f"Failed for: {input_text}"

    def test_convert_standalone_roman_numerals(self, refiner):
        """Test standalone roman numeral conversion."""
        text = "Results for I, II, and III are positive."
        result = refiner._convert_roman_numerals(text)
        # Standalone roman numerals should be converted
        assert "One" in result or "Two" in result or "Three" in result

    def test_dont_convert_roman_in_words(self, refiner):
        """Test that roman numerals inside words aren't converted."""
        text = "INVALID data fromIXIN compound"
        result = refiner._convert_roman_numerals(text)
        # Should not break words containing I, V, X, etc.
        assert "INVALID" in result or "Invalid" in result  # May be case-normalized

    def test_clean_special_characters(self, refiner):
        """Test special character cleanup."""
        # Using unicode escapes to avoid syntax issues
        text = "Text with \u2014 em-dash and \u201csmart quotes\u201d and \u2018apostrophes\u2019."
        result = refiner._clean_special_characters(text)
        assert "\u2014" not in result  # em-dash
        assert "\u201c" not in result  # smart quote open
        assert "\u2018" not in result  # smart apostrophe
        assert "-" in result

    def test_normalize_whitespace(self, refiner):
        """Test whitespace normalization."""
        text = "Text  with   multiple    spaces\n\n\n\nand many newlines"
        result = refiner._normalize_whitespace(text)
        assert "  " not in result  # No double spaces
        assert "\n\n\n" not in result  # Max two newlines

    async def test_full_refine_workflow(self, refiner):
        """Test complete refinement workflow."""
        markdown_text = """# Summary

**Metformin** shows promise for *long COVID* treatment [1].

## Phase I Trials

Research (Smith et al., 2023) indicates [2,3]:
- 50% improvement
- Low side effects

Check [this study](https://example.com) for details.

# References
[1] Smith, J. et al. (2023)
[2] Jones, K. (2022)
"""

        result = await refiner.refine_for_audio(markdown_text)

        # Check markdown removed
        assert "#" not in result
        assert "**" not in result
        assert "*" not in result

        # Check citations removed
        assert "[1]" not in result
        assert "(Smith et al., 2023)" not in result

        # Check roman numerals converted
        assert "Phase One" in result

        # Check references section removed
        assert "References" not in result
        assert "Smith, J. et al." not in result

        # Check content preserved
        assert "Metformin" in result
        assert "long COVID" in result

    async def test_convenience_function(self):
        """Test convenience function."""
        text = "**Bold** text with [link](url)"
        result = await refine_text_for_audio(text)
        assert "**" not in result
        assert "[link]" not in result
        assert "Bold" in result

    async def test_empty_text(self, refiner):
        """Test handling of empty text."""
        assert await refiner.refine_for_audio("") == ""
        assert await refiner.refine_for_audio("   ") == ""

    async def test_no_references_section(self, refiner):
        """Test text without References section."""
        text = "Main content without references."
        result = await refiner.refine_for_audio(text)
        assert "Main content without references" in result

    def test_multiple_reference_formats(self, refiner):
        """Test different References section formats."""
        formats = [
            ("# References\nContent", True),  # Markdown header - will be removed
            ("## References\nContent", True),  # Markdown header - will be removed
            ("**References**\nContent", True),  # Bold heading - will be removed
            ("References:\nContent", False),  # Standalone without markers - NOT removed (edge case)
        ]

        for format_text, should_remove in formats:
            text = f"Main content\n{format_text}"
            result = refiner._remove_references_sections(text)
            assert "Main content" in result
            if should_remove:
                assert "References" not in result or result.count("References") == 0
            # Standalone "References:" without markers is an edge case we don't handle

    def test_preserve_paragraph_structure(self, refiner):
        """Test that paragraph structure is preserved."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."

        result = refiner._normalize_whitespace(text)
        # Should have paragraph breaks (double newlines)
        assert "\n\n" in result
        # But not excessive newlines
        assert "\n\n\n" not in result

    @patch('src.agents.audio_refiner.get_pydantic_ai_model')
    async def test_llm_polish_disabled_by_default(self, mock_get_model, refiner):
        """Test that LLM polish is not called by default."""
        text = "Test text"
        result = await refiner.refine_for_audio(text, use_llm_polish=False)

        # LLM should not be called when disabled
        mock_get_model.assert_not_called()
        assert "Test text" in result

    @patch('src.agents.audio_refiner.Agent')
    @patch('src.agents.audio_refiner.get_pydantic_ai_model')
    async def test_llm_polish_enabled(self, mock_get_model, mock_agent_class, refiner):
        """Test that LLM polish is called when enabled."""
        # Setup mock
        mock_model = Mock()
        mock_get_model.return_value = mock_model

        mock_agent_instance = Mock()
        mock_result = Mock()
        mock_result.output = "Polished text"
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        # Test with LLM polish enabled
        text = "**Test** text"
        result = await refiner.refine_for_audio(text, use_llm_polish=True)

        # Verify LLM was called
        mock_get_model.assert_called_once()
        mock_agent_class.assert_called_once()
        mock_agent_instance.run.assert_called_once()

        assert result == "Polished text"

    @patch('src.agents.audio_refiner.Agent')
    @patch('src.agents.audio_refiner.get_pydantic_ai_model')
    async def test_llm_polish_graceful_fallback(self, mock_get_model, mock_agent_class, refiner):
        """Test graceful fallback when LLM polish fails."""
        # Setup mock to raise exception
        mock_get_model.return_value = Mock()
        mock_agent_instance = Mock()
        mock_agent_instance.run = AsyncMock(side_effect=Exception("API Error"))
        mock_agent_class.return_value = mock_agent_instance

        # Test with LLM polish enabled but failing
        text = "Test text"
        result = await refiner.refine_for_audio(text, use_llm_polish=True)

        # Should fall back to rule-based output
        assert "Test text" in result
        assert result != ""  # Should not be empty

    async def test_convenience_function_with_llm_polish(self):
        """Test convenience function with LLM polish parameter."""
        with patch.object(AudioRefiner, 'refine_for_audio') as mock_refine:
            mock_refine.return_value = AsyncMock(return_value="Refined text")()

            # Test without LLM polish
            result = await refine_text_for_audio("Test", use_llm_polish=False)
            mock_refine.assert_called_with("Test", use_llm_polish=False)

            # Test with LLM polish
            result = await refine_text_for_audio("Test", use_llm_polish=True)
            mock_refine.assert_called_with("Test", use_llm_polish=True)
