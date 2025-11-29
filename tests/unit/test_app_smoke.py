"""Smoke tests for the Gradio app.

These tests verify the app can start without crashing.
They catch configuration errors like invalid Gradio parameters
that wouldn't be caught by unit tests.
"""

import pytest


@pytest.mark.unit
class TestAppSmoke:
    """Smoke tests for app initialization."""

    def test_app_creates_demo(self) -> None:
        """App should create Gradio demo without crashing.

        This catches:
        - Invalid Gradio component parameters
        - Import errors
        - Configuration issues
        """
        # Skip if gradio not fully installed (CI may not have all deps)
        pytest.importorskip("gradio")
        pytest.importorskip("typer")  # Gradio CLI dependency

        from src.app import create_demo

        # OAuth dependencies may not be available in test environment
        # This is acceptable - OAuth is optional functionality
        # Also skip if HF_TOKEN is not set (required for Gradio OAuth mocking)
        import os
        if not os.getenv("HF_TOKEN"):
            pytest.skip("HF_TOKEN not set - required for Gradio OAuth mocking in tests")
        
        try:
            demo = create_demo()
            assert demo is not None
        except ImportError as e:
            if "oauth" in str(e).lower() or "itsdangerous" in str(e).lower():
                pytest.skip(f"OAuth dependencies not available: {e}")
            raise
        except ValueError as e:
            if "HF_TOKEN" in str(e) or "huggingface-cli login" in str(e):
                pytest.skip(f"HF authentication not available: {e}")
            raise

    def test_mcp_tools_importable(self) -> None:
        """MCP tool functions should be importable.

        Ensures the MCP server can expose these tools.
        """
        from src.mcp_tools import (
            analyze_hypothesis,
            search_all_sources,
            search_clinical_trials,
            search_europepmc,
            search_pubmed,
        )

        # Just verify they're callable
        assert callable(search_pubmed)
        assert callable(search_clinical_trials)
        assert callable(search_europepmc)
        assert callable(search_all_sources)
        assert callable(analyze_hypothesis)
