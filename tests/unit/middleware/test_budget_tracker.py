"""Unit tests for BudgetTracker and BudgetStatus."""

import time

import pytest

from src.middleware.budget_tracker import BudgetStatus, BudgetTracker


@pytest.mark.unit
class TestBudgetStatus:
    """Tests for BudgetStatus model."""

    def test_initialization(self) -> None:
        """BudgetStatus should initialize with default values."""
        budget = BudgetStatus()
        assert budget.tokens_used == 0
        assert budget.tokens_limit == 100000
        assert budget.time_elapsed_seconds == 0.0
        assert budget.time_limit_seconds == 600.0
        assert budget.iterations == 0
        assert budget.iterations_limit == 10

    def test_custom_limits(self) -> None:
        """BudgetStatus should accept custom limits."""
        budget = BudgetStatus(tokens_limit=50000, time_limit_seconds=300.0, iterations_limit=5)
        assert budget.tokens_limit == 50000
        assert budget.time_limit_seconds == 300.0
        assert budget.iterations_limit == 5

    def test_is_exceeded_tokens(self) -> None:
        """is_exceeded should return True when tokens limit is reached."""
        budget = BudgetStatus(tokens_limit=100, tokens_used=100)
        assert budget.is_exceeded() is True

    def test_is_exceeded_time(self) -> None:
        """is_exceeded should return True when time limit is reached."""
        budget = BudgetStatus(time_limit_seconds=60.0, time_elapsed_seconds=60.0)
        assert budget.is_exceeded() is True

    def test_is_exceeded_iterations(self) -> None:
        """is_exceeded should return True when iterations limit is reached."""
        budget = BudgetStatus(iterations_limit=5, iterations=5)
        assert budget.is_exceeded() is True

    def test_is_exceeded_not_exceeded(self) -> None:
        """is_exceeded should return False when no limits are exceeded."""
        budget = BudgetStatus(
            tokens_used=50, tokens_limit=100, time_elapsed_seconds=30.0, time_limit_seconds=60.0
        )
        assert budget.is_exceeded() is False

    def test_remaining_tokens(self) -> None:
        """remaining_tokens should calculate remaining token budget."""
        budget = BudgetStatus(tokens_limit=100, tokens_used=30)
        assert budget.remaining_tokens() == 70

    def test_remaining_tokens_exceeded(self) -> None:
        """remaining_tokens should return negative if exceeded."""
        budget = BudgetStatus(tokens_limit=100, tokens_used=150)
        assert budget.remaining_tokens() == -50

    def test_remaining_time_seconds(self) -> None:
        """remaining_time_seconds should calculate remaining time."""
        budget = BudgetStatus(time_limit_seconds=60.0, time_elapsed_seconds=30.0)
        assert budget.remaining_time_seconds() == 30.0

    def test_remaining_iterations(self) -> None:
        """remaining_iterations should calculate remaining iterations."""
        budget = BudgetStatus(iterations_limit=10, iterations=3)
        assert budget.remaining_iterations() == 7


@pytest.mark.unit
class TestBudgetTracker:
    """Tests for BudgetTracker class."""

    def test_initialization(self) -> None:
        """BudgetTracker should initialize with empty budgets."""
        tracker = BudgetTracker()
        assert tracker._budgets == {}
        assert tracker._start_times == {}
        assert tracker._global_budget is None

    def test_create_budget(self) -> None:
        """create_budget should create a budget for a loop."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=50000, time_limit_seconds=300.0)

        assert "loop1" in tracker._budgets
        assert tracker._budgets["loop1"].tokens_limit == 50000
        assert tracker._budgets["loop1"].time_limit_seconds == 300.0

    def test_get_budget(self) -> None:
        """get_budget should return budget for a loop."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1")
        budget = tracker.get_budget("loop1")

        assert budget is not None
        assert isinstance(budget, BudgetStatus)

    def test_get_budget_not_found(self) -> None:
        """get_budget should return None if loop not found."""
        tracker = BudgetTracker()
        budget = tracker.get_budget("nonexistent")
        assert budget is None

    def test_add_tokens(self) -> None:
        """add_tokens should increment token usage."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1")
        tracker.add_tokens("loop1", 1000)

        budget = tracker.get_budget("loop1")
        assert budget is not None
        assert budget.tokens_used == 1000

    def test_add_tokens_multiple(self) -> None:
        """add_tokens should accumulate token usage."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1")
        tracker.add_tokens("loop1", 1000)
        tracker.add_tokens("loop1", 500)

        budget = tracker.get_budget("loop1")
        assert budget is not None
        assert budget.tokens_used == 1500

    def test_start_timer(self) -> None:
        """start_timer should record start time."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1")
        tracker.start_timer("loop1")

        assert "loop1" in tracker._start_times
        assert isinstance(tracker._start_times["loop1"], float)

    def test_update_timer(self) -> None:
        """update_timer should update elapsed time."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1")
        tracker.start_timer("loop1")

        time.sleep(0.1)  # Sleep briefly
        tracker.update_timer("loop1")

        budget = tracker.get_budget("loop1")
        assert budget is not None
        assert budget.time_elapsed_seconds >= 0.1

    def test_increment_iteration(self) -> None:
        """increment_iteration should increment iteration count."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1")
        tracker.increment_iteration("loop1")
        tracker.increment_iteration("loop1")

        budget = tracker.get_budget("loop1")
        assert budget is not None
        assert budget.iterations == 2

    def test_check_budget_not_exceeded(self) -> None:
        """check_budget should return (False, '') when not exceeded."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=1000, time_limit_seconds=60.0)
        tracker.add_tokens("loop1", 500)
        tracker.start_timer("loop1")

        exceeded, reason = tracker.check_budget("loop1")
        assert exceeded is False
        assert reason == ""

    def test_check_budget_exceeded_tokens(self) -> None:
        """check_budget should detect token limit exceeded."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=1000)
        tracker.add_tokens("loop1", 1000)

        exceeded, reason = tracker.check_budget("loop1")
        assert exceeded is True
        assert "tokens" in reason

    def test_check_budget_exceeded_time(self) -> None:
        """check_budget should detect time limit exceeded."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", time_limit_seconds=0.01)  # Very short limit
        tracker.start_timer("loop1")
        time.sleep(0.02)  # Sleep longer than limit

        exceeded, reason = tracker.check_budget("loop1")
        assert exceeded is True
        assert "time" in reason

    def test_check_budget_exceeded_iterations(self) -> None:
        """check_budget should detect iteration limit exceeded."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", iterations_limit=5)
        for _ in range(5):
            tracker.increment_iteration("loop1")

        exceeded, reason = tracker.check_budget("loop1")
        assert exceeded is True
        assert "iterations" in reason

    def test_can_continue(self) -> None:
        """can_continue should return True when budget not exceeded."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1")
        assert tracker.can_continue("loop1") is True

    def test_can_continue_exceeded(self) -> None:
        """can_continue should return False when budget exceeded."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=1000)
        tracker.add_tokens("loop1", 1000)

        assert tracker.can_continue("loop1") is False

    def test_get_budget_summary(self) -> None:
        """get_budget_summary should return formatted string."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=1000, time_limit_seconds=60.0)
        tracker.add_tokens("loop1", 500)
        tracker.start_timer("loop1")
        tracker.update_timer("loop1")

        summary = tracker.get_budget_summary("loop1")
        assert "loop1" in summary
        assert "500" in summary
        assert "1000" in summary

    def test_reset_budget(self) -> None:
        """reset_budget should reset counters but keep limits."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=1000, time_limit_seconds=60.0)
        tracker.add_tokens("loop1", 500)
        tracker.increment_iteration("loop1")
        tracker.start_timer("loop1")

        tracker.reset_budget("loop1")

        budget = tracker.get_budget("loop1")
        assert budget is not None
        assert budget.tokens_used == 0
        assert budget.iterations == 0
        assert budget.tokens_limit == 1000  # Limits preserved

    def test_set_global_budget(self) -> None:
        """set_global_budget should set global budget."""
        tracker = BudgetTracker()
        tracker.set_global_budget(tokens_limit=50000, time_limit_seconds=300.0)

        global_budget = tracker.get_global_budget()
        assert global_budget is not None
        assert global_budget.tokens_limit == 50000
        assert global_budget.time_limit_seconds == 300.0

    def test_add_global_tokens(self) -> None:
        """add_global_tokens should increment global token usage."""
        tracker = BudgetTracker()
        tracker.set_global_budget()
        tracker.add_global_tokens(1000)

        global_budget = tracker.get_global_budget()
        assert global_budget is not None
        assert global_budget.tokens_used == 1000

    def test_estimate_tokens(self) -> None:
        """estimate_tokens should estimate token count (~4 chars per token)."""
        tracker = BudgetTracker()
        # 100 characters should be ~25 tokens
        tokens = tracker.estimate_tokens("a" * 100)
        assert tokens == 25  # 100 / 4

    def test_estimate_llm_call_tokens(self) -> None:
        """estimate_llm_call_tokens should sum prompt and response tokens."""
        tracker = BudgetTracker()
        prompt = "a" * 100  # ~25 tokens
        response = "b" * 200  # ~50 tokens
        total = tracker.estimate_llm_call_tokens(prompt, response)
        assert total == 75  # 25 + 50
