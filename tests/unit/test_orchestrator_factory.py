"""Unit tests for Orchestrator Factory."""

from unittest.mock import ANY, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from src.orchestrator import Orchestrator
from src.orchestrator_factory import create_orchestrator


@pytest.fixture
def mock_settings():
    with patch("src.orchestrator_factory.settings", autospec=True) as mock_settings:
        mock_settings.has_openai_key = False
        mock_settings.use_graph_execution = False
        mock_settings.default_time_limit_minutes = 10
        mock_settings.default_iterations_limit = 10
        yield mock_settings


@pytest.fixture
def mock_magentic_cls():
    with patch("src.orchestrator_factory._get_magentic_orchestrator_class") as mock:
        # The mock returns a class (callable), which returns an instance
        mock_class = MagicMock()
        mock.return_value = mock_class
        yield mock_class


@pytest.fixture
def mock_graph_cls():
    with patch("src.orchestrator_factory._get_graph_orchestrator_class") as mock:
        mock_class = MagicMock()
        mock.return_value = mock_class
        yield mock_class


@pytest.fixture
def mock_handlers():
    return MagicMock(), MagicMock()


def test_create_orchestrator_simple_explicit(mock_settings, mock_handlers):
    """Test explicit simple mode."""
    search, judge = mock_handlers
    orch = create_orchestrator(search_handler=search, judge_handler=judge, mode="simple")
    assert isinstance(orch, Orchestrator)


def test_create_orchestrator_advanced_explicit(mock_settings, mock_handlers, mock_magentic_cls):
    """Test explicit advanced mode."""
    # Ensure has_openai_key is True so it doesn't error if we add checks
    mock_settings.has_openai_key = True

    orch = create_orchestrator(mode="advanced")
    # verify instantiated
    mock_magentic_cls.assert_called_once()
    assert orch == mock_magentic_cls.return_value


def test_create_orchestrator_auto_advanced(mock_settings, mock_magentic_cls):
    """Test auto-detect advanced mode when OpenAI key exists."""
    mock_settings.has_openai_key = True

    orch = create_orchestrator()
    mock_magentic_cls.assert_called_once()
    assert orch == mock_magentic_cls.return_value


def test_create_orchestrator_auto_simple(mock_settings, mock_handlers):
    """Test auto-detect simple mode when no paid keys."""
    mock_settings.has_openai_key = False

    search, judge = mock_handlers
    orch = create_orchestrator(search_handler=search, judge_handler=judge)
    assert isinstance(orch, Orchestrator)


def test_create_orchestrator_graph_mode(mock_settings, mock_handlers, mock_graph_cls):
    """Graph mode should return GraphOrchestrator when enabled."""
    mock_settings.use_graph_execution = False
    mock_settings.default_time_limit_minutes = 5
    mock_settings.default_iterations_limit = 3

    search, judge = mock_handlers
    orch = create_orchestrator(
        search_handler=search,
        judge_handler=judge,
        mode="simple",
        graph_mode="iterative",
        use_graph=True,
    )

    mock_graph_cls.assert_called_once_with(
        mode="iterative",
        max_iterations=ANY,
        max_time_minutes=5,
        use_graph=True,
        search_handler=search,
        judge_handler=judge,
    )
    assert orch == mock_graph_cls.return_value
