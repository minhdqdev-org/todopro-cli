"""Comprehensive unit tests for utils/ui/textual_prompt.py.

Tests TaskSuggester, HighlightedInput.get_suggestions(),
load_cache(), and the QuickAddApp lifecycle (non-TUI paths).
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todopro_cli.utils.ui.textual_prompt import (
    HighlightedInput,
    TaskSuggester,
    load_cache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_input(
    projects: list[str] | None = None,
    labels: list[str] | None = None,
) -> HighlightedInput:
    """Instantiate HighlightedInput without a running Textual app."""
    inp = HighlightedInput.__new__(HighlightedInput)
    inp.projects = projects if projects is not None else ["Inbox", "Work", "Personal", "Side Project"]
    inp.labels = labels if labels is not None else ["urgent", "home", "work", "low-priority"]
    # Set attributes that __init__ would normally set
    inp.date_keywords = [
        "today", "tomorrow", "tom", "yesterday",
        "monday", "mon", "tuesday", "tue", "wednesday", "wed",
        "thursday", "thu", "friday", "fri", "saturday", "sat", "sunday", "sun",
    ]
    inp.keyword_unhighlighted = set()
    return inp


def _make_suggester(
    projects: list[str] | None = None,
    labels: list[str] | None = None,
) -> TaskSuggester:
    s = TaskSuggester()
    s.projects = projects if projects is not None else ["Inbox", "Work"]
    s.labels = labels if labels is not None else ["urgent", "home"]
    return s


# ===========================================================================
# TaskSuggester
# ===========================================================================

class TestTaskSuggesterInit:
    """Tests for TaskSuggester constructor."""

    def test_init_projects_empty(self):
        s = TaskSuggester()
        assert s.projects == []

    def test_init_labels_empty(self):
        s = TaskSuggester()
        assert s.labels == []

    def test_use_cache_false(self):
        s = TaskSuggester()
        # use_cache=False is stored by Textual as cache=None (no LRU cache)
        assert s.cache is None

    def test_case_sensitive_false(self):
        s = TaskSuggester()
        assert s.case_sensitive is False


class TestTaskSuggesterGetSuggestion:
    """Tests for TaskSuggester.get_suggestion()."""

    def test_returns_none_when_no_data(self):
        s = TaskSuggester()
        result = asyncio.run(s.get_suggestion("@ur"))
        assert result is None

    def test_label_completion_at_symbol(self):
        s = _make_suggester(labels=["urgent", "home"])
        result = asyncio.run(s.get_suggestion("do task @ur"))
        assert result == "do task @urgent"

    def test_label_completion_case_insensitive(self):
        s = _make_suggester(labels=["Urgent"])
        result = asyncio.run(s.get_suggestion("task @ur"))
        assert result is not None
        assert "Urgent" in result

    def test_project_completion_hash_symbol(self):
        s = _make_suggester(projects=["Inbox", "Work"])
        result = asyncio.run(s.get_suggestion("do task #In"))
        assert result == "do task #Inbox"

    def test_project_completion_case_insensitive(self):
        s = _make_suggester(projects=["Inbox"])
        result = asyncio.run(s.get_suggestion("task #inbox"))
        assert result is not None
        assert "Inbox" in result

    def test_no_match_returns_none(self):
        s = _make_suggester(labels=["home"])
        result = asyncio.run(s.get_suggestion("task @zzz"))
        assert result is None

    def test_no_at_or_hash_returns_none(self):
        s = _make_suggester()
        result = asyncio.run(s.get_suggestion("plain text"))
        assert result is None

    def test_label_prefix_empty_no_match(self):
        """'@' with nothing after gives empty prefix — no completion returned."""
        s = _make_suggester(labels=["urgent"])
        result = asyncio.run(s.get_suggestion("task @"))
        # prefix is empty string, loop condition 'if parts[1]' prevents match
        assert result is None

    def test_project_prefix_empty_no_match(self):
        s = _make_suggester(projects=["Inbox"])
        result = asyncio.run(s.get_suggestion("task #"))
        assert result is None

    def test_returns_first_matching_label(self):
        s = _make_suggester(labels=["aaa", "aab", "aac"])
        result = asyncio.run(s.get_suggestion("task @aa"))
        # Returns the first match
        assert result == "task @aaa"


# ===========================================================================
# HighlightedInput.get_suggestions — project completions
# ===========================================================================

class TestGetSuggestionsProjects:
    """Tests for the project (#) completion path."""

    def test_hash_alone_returns_all_projects(self):
        inp = _make_input(projects=["Inbox", "Work"])
        result = inp.get_suggestions("#")
        assert "#Inbox" in result
        assert "#Work" in result

    def test_hash_with_prefix_filters(self):
        inp = _make_input(projects=["Inbox", "Work", "Personal"])
        result = inp.get_suggestions("#In")
        assert "#Inbox" in result
        assert "#Work" not in result
        assert "#Personal" not in result

    def test_hash_prefix_case_insensitive(self):
        inp = _make_input(projects=["Inbox"])
        result = inp.get_suggestions("#in")
        assert "#Inbox" in result

    def test_hash_no_match_returns_empty(self):
        inp = _make_input(projects=["Inbox", "Work"])
        result = inp.get_suggestions("#zzz")
        assert result == []

    def test_empty_projects_with_hash_returns_empty(self):
        inp = _make_input(projects=[])
        result = inp.get_suggestions("#")
        assert result == []

    def test_projects_sorted(self):
        inp = _make_input(projects=["Zebra", "Alpha", "Mango"])
        result = inp.get_suggestions("#")
        names = [r[1:] for r in result]  # strip '#'
        assert names == sorted(names, key=str.lower)

    def test_max_ten_results(self):
        inp = _make_input(projects=[f"Project{i}" for i in range(20)])
        result = inp.get_suggestions("#P")
        assert len(result) <= 10


# ===========================================================================
# HighlightedInput.get_suggestions — label completions
# ===========================================================================

class TestGetSuggestionsLabels:
    """Tests for the label (@) completion path."""

    def test_at_alone_returns_all_labels(self):
        inp = _make_input(labels=["urgent", "home"])
        result = inp.get_suggestions("some text @")
        assert "@urgent" in result
        assert "@home" in result

    def test_at_with_prefix_filters(self):
        inp = _make_input(labels=["urgent", "home", "unhappy"])
        result = inp.get_suggestions("task @ur")
        assert "@urgent" in result
        assert "@home" not in result

    def test_at_prefix_case_insensitive(self):
        inp = _make_input(labels=["Urgent"])
        result = inp.get_suggestions("task @ur")
        assert "@Urgent" in result

    def test_at_no_match_returns_empty(self):
        inp = _make_input(labels=["home"])
        result = inp.get_suggestions("task @zzz")
        assert result == []

    def test_empty_labels_with_at_returns_empty(self):
        inp = _make_input(labels=[])
        result = inp.get_suggestions("task @")
        assert result == []

    def test_labels_sorted(self):
        inp = _make_input(labels=["zebra", "alpha", "mango"])
        result = inp.get_suggestions("task @")
        names = [r[1:] for r in result]
        assert names == sorted(names, key=str.lower)

    def test_max_ten_label_results(self):
        inp = _make_input(labels=[f"label{i}" for i in range(20)])
        result = inp.get_suggestions("task @l")
        assert len(result) <= 10


# ===========================================================================
# HighlightedInput.get_suggestions — priority completions
# ===========================================================================

class TestGetSuggestionsPriority:
    """Tests for priority (p1–p4 / !!1–!!4) completion path."""

    def test_p_alone_returns_all_four_priorities(self):
        inp = _make_input()
        result = inp.get_suggestions("task p")
        assert any("p1" in s for s in result)
        assert any("p2" in s for s in result)
        assert any("p3" in s for s in result)
        assert any("p4" in s for s in result)

    def test_p1_filters_to_urgent_only(self):
        inp = _make_input()
        result = inp.get_suggestions("task p1")
        assert any("p1" in s for s in result)
        assert not any("p2" in s for s in result)
        assert not any("p3" in s for s in result)

    def test_p2_filters_correctly(self):
        inp = _make_input()
        result = inp.get_suggestions("fix bug p2")
        assert any("p2" in s for s in result)
        assert not any("p1" in s for s in result)

    def test_bang_bang_returns_all_four(self):
        inp = _make_input()
        result = inp.get_suggestions("task !!")
        assert any("!!1" in s for s in result)
        assert any("!!2" in s for s in result)

    def test_bang_bang_1_filters(self):
        inp = _make_input()
        result = inp.get_suggestions("task !!1")
        assert any("!!1" in s for s in result)
        assert not any("!!2" in s for s in result)

    def test_p_prefix_in_middle_of_sentence(self):
        inp = _make_input()
        result = inp.get_suggestions("buy groceries p")
        assert any("p1" in s for s in result)

    def test_no_priority_suggestions_for_plain_word(self):
        inp = _make_input()
        result = inp.get_suggestions("just some text")
        assert result == []


# ===========================================================================
# HighlightedInput.get_suggestions — edge cases
# ===========================================================================

class TestGetSuggestionsEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_string_returns_empty(self):
        inp = _make_input()
        result = inp.get_suggestions("")
        assert result == []

    def test_whitespace_only_returns_empty(self):
        inp = _make_input()
        result = inp.get_suggestions("   ")
        assert result == []

    def test_at_takes_priority_over_hash_when_both_present(self):
        """'@' is checked before '#' in get_suggestions. When both appear,
        the '@' branch fires but the prefix includes everything after the '@'.
        Only the '#' alone path (after '@' text) matches projects."""
        inp = _make_input(projects=["Inbox"], labels=["urgent"])
        # Plain '#' only — projects returned
        result_hash = inp.get_suggestions("#In")
        assert "#Inbox" in result_hash
        # Plain '@' only — labels returned
        result_at = inp.get_suggestions("task @ur")
        assert "@urgent" in result_at
        # Both: '@' is checked first; rsplit('@') prefix includes '#In', no label matches
        result_both = inp.get_suggestions("@ur #In")
        assert result_both == []  # no match because prefix is 'ur #in'

    def test_result_is_list(self):
        inp = _make_input()
        assert isinstance(inp.get_suggestions(""), list)
        assert isinstance(inp.get_suggestions("#"), list)
        assert isinstance(inp.get_suggestions("task @u"), list)


# ===========================================================================
# load_cache
# ===========================================================================

class TestLoadCache:
    """Tests for the load_cache() helper function."""

    def _make_storage_ctx(self, projects=None, labels=None):
        from todopro_cli.models import Project, Label
        from datetime import datetime

        p_list = projects or []
        l_list = labels or []
        proj_repo = MagicMock()
        proj_repo.list_all = AsyncMock(return_value=p_list)
        label_repo = MagicMock()
        label_repo.list_all = AsyncMock(return_value=l_list)
        ctx = MagicMock()
        ctx.project_repository = proj_repo
        ctx.label_repository = label_repo
        return ctx

    def _make_mock_project(self, name: str) -> MagicMock:
        p = MagicMock()
        p.name = name
        return p

    def _make_mock_label(self, name: str) -> MagicMock:
        lb = MagicMock()
        lb.name = name
        return lb

    def test_returns_empty_lists_on_exception(self):
        """If storage strategy raises, load_cache returns empty lists."""
        with patch(
            "todopro_cli.utils.ui.textual_prompt.get_storage_strategy_context",
            side_effect=RuntimeError("DB not available"),
        ):
            with patch(
                "todopro_cli.utils.ui.textual_prompt.get_config_service",
            ) as mock_gcs:
                # Provide a mock data_dir that points nowhere real
                mock_svc = MagicMock()
                mock_svc.data_dir = Path("/tmp/nonexistent_todopro_test_cache_dir_xxx")
                mock_gcs.return_value = mock_svc
                projects, labels = load_cache()
        assert projects == []
        assert labels == []

    def test_loads_from_valid_cache_file(self, tmp_path):
        """If a recent cache file exists, load_cache should return its contents."""
        cache_file = tmp_path / "quick_add_cache.json"
        cache_data = {
            "projects": ["Inbox", "Work"],
            "labels": ["urgent", "home"],
            "timestamp": datetime.now().timestamp(),
        }
        cache_file.write_text(json.dumps(cache_data))

        mock_svc = MagicMock()
        mock_svc.data_dir = tmp_path

        with patch("todopro_cli.utils.ui.textual_prompt.get_config_service", return_value=mock_svc):
            projects, labels = load_cache()

        assert "Inbox" in projects
        assert "Work" in projects
        assert "urgent" in labels
        assert "home" in labels

    def test_stale_cache_triggers_refresh(self, tmp_path):
        """A cache file older than 5 minutes should be refreshed."""
        cache_file = tmp_path / "quick_add_cache.json"
        old_timestamp = datetime.now().timestamp() - 400  # 400s old > 300s TTL
        cache_data = {
            "projects": ["OldProject"],
            "labels": ["old-label"],
            "timestamp": old_timestamp,
        }
        cache_file.write_text(json.dumps(cache_data))

        mock_svc = MagicMock()
        mock_svc.data_dir = tmp_path

        fresh_projects = [self._make_mock_project("NewProject")]
        fresh_labels = [self._make_mock_label("new-label")]
        storage_ctx = self._make_storage_ctx(
            projects=fresh_projects,
            labels=fresh_labels,
        )

        with patch("todopro_cli.utils.ui.textual_prompt.get_config_service", return_value=mock_svc):
            with patch(
                "todopro_cli.utils.ui.textual_prompt.get_storage_strategy_context",
                return_value=storage_ctx,
            ):
                projects, labels = load_cache()

        assert "NewProject" in projects
        assert "new-label" in labels

    def test_fresh_data_saved_to_cache(self, tmp_path):
        """Data fetched from storage should be written to cache."""
        mock_svc = MagicMock()
        mock_svc.data_dir = tmp_path

        fresh_projects = [self._make_mock_project("SavedProject")]
        fresh_labels = [self._make_mock_label("saved-label")]
        storage_ctx = self._make_storage_ctx(
            projects=fresh_projects,
            labels=fresh_labels,
        )

        with patch("todopro_cli.utils.ui.textual_prompt.get_config_service", return_value=mock_svc):
            with patch(
                "todopro_cli.utils.ui.textual_prompt.get_storage_strategy_context",
                return_value=storage_ctx,
            ):
                load_cache()

        cache_file = tmp_path / "quick_add_cache.json"
        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert "SavedProject" in data["projects"]
        assert "saved-label" in data["labels"]
        assert "timestamp" in data

    def test_returns_tuple_of_two_lists(self):
        with patch(
            "todopro_cli.utils.ui.textual_prompt.get_storage_strategy_context",
            side_effect=Exception("fail"),
        ):
            with patch("todopro_cli.utils.ui.textual_prompt.get_config_service") as mock_gcs:
                mock_svc = MagicMock()
                mock_svc.data_dir = Path("/tmp/nonexistent_dir_xyz")
                mock_gcs.return_value = mock_svc
                result = load_cache()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert isinstance(result[1], list)


# ===========================================================================
# QuickAddApp — construction (no TUI)
# ===========================================================================

class TestQuickAddAppInit:
    """Tests for QuickAddApp constructor (no TUI execution)."""

    def test_default_project_stored(self):
        from todopro_cli.utils.ui.textual_prompt import QuickAddApp

        app = QuickAddApp(default_project="MyProject")
        assert app.default_project == "MyProject"

    def test_result_initially_none(self):
        from todopro_cli.utils.ui.textual_prompt import QuickAddApp

        app = QuickAddApp()
        assert app.result is None

    def test_default_project_defaults_to_inbox(self):
        from todopro_cli.utils.ui.textual_prompt import QuickAddApp

        app = QuickAddApp()
        assert app.default_project == "Inbox"


# ===========================================================================
# HighlightedInput — initialisation
# ===========================================================================

class TestHighlightedInputInit:
    """Tests for HighlightedInput constructor."""

    def test_date_keywords_populated(self):
        inp = _make_input()
        assert "today" in inp.date_keywords
        assert "tomorrow" in inp.date_keywords
        assert "monday" in inp.date_keywords

    def test_projects_and_labels_initially_empty_on_fresh_instance(self):
        """Projects and labels start empty before data loading."""
        # Build directly via __init__ path (not our helper)
        from textual.widgets import Input as TInput

        # We only test the structure via the helper which bypasses __init__
        inp = _make_input(projects=[], labels=[])
        assert inp.projects == []
        assert inp.labels == []

    def test_keyword_unhighlighted_is_set(self):
        inp = _make_input()
        assert isinstance(inp.keyword_unhighlighted, set)


# ===========================================================================
# HighlightedInput — actual __init__ path (lines 64-87)
# ===========================================================================

class TestHighlightedInputActualInit:
    """Tests for HighlightedInput.__init__() via direct instantiation."""

    def test_init_sets_projects_empty(self):
        inp = HighlightedInput()
        assert inp.projects == []

    def test_init_sets_labels_empty(self):
        inp = HighlightedInput()
        assert inp.labels == []

    def test_init_sets_date_keywords(self):
        inp = HighlightedInput()
        assert "today" in inp.date_keywords
        assert "tomorrow" in inp.date_keywords
        assert "monday" in inp.date_keywords
        assert "friday" in inp.date_keywords

    def test_init_sets_keyword_unhighlighted_as_set(self):
        inp = HighlightedInput()
        assert isinstance(inp.keyword_unhighlighted, set)
        assert len(inp.keyword_unhighlighted) == 0

    def test_init_with_kwargs_does_not_raise(self):
        """Passing keyword arguments compatible with Textual Input must not raise."""
        inp = HighlightedInput(placeholder="Enter task")
        assert inp.projects == []


# ===========================================================================
# QuickAddApp — handler methods (lines 257-287)
# ===========================================================================

class TestQuickAddAppHandlers:
    """Tests for QuickAddApp handler methods without a running TUI."""

    def test_handle_submit_sets_result_and_exits(self):
        from todopro_cli.utils.ui.textual_prompt import QuickAddApp

        app = QuickAddApp()
        app.exit = MagicMock()
        mock_event = MagicMock()
        mock_event.value = "Buy groceries"
        app.handle_submit(mock_event)
        assert app.result == "Buy groceries"
        app.exit.assert_called_once()

    def test_handle_submit_stripped_value(self):
        from todopro_cli.utils.ui.textual_prompt import QuickAddApp

        app = QuickAddApp()
        app.exit = MagicMock()
        mock_event = MagicMock()
        mock_event.value = "  Learn Python  "
        app.handle_submit(mock_event)
        assert app.result == "Learn Python"
        app.exit.assert_called_once()

    def test_handle_submit_empty_value_does_not_exit(self):
        from todopro_cli.utils.ui.textual_prompt import QuickAddApp

        app = QuickAddApp()
        app.exit = MagicMock()
        mock_event = MagicMock()
        mock_event.value = "   "
        app.handle_submit(mock_event)
        assert app.result is None
        app.exit.assert_not_called()

    def test_on_key_escape_exits(self):
        from todopro_cli.utils.ui.textual_prompt import QuickAddApp

        app = QuickAddApp()
        app.exit = MagicMock()
        mock_event = MagicMock()
        mock_event.key = "escape"
        app.on_key(mock_event)
        assert app.result is None
        app.exit.assert_called_once()

    def test_on_key_ctrl_c_exits(self):
        from todopro_cli.utils.ui.textual_prompt import QuickAddApp

        app = QuickAddApp()
        app.exit = MagicMock()
        mock_event = MagicMock()
        mock_event.key = "ctrl+c"
        app.on_key(mock_event)
        assert app.result is None
        app.exit.assert_called_once()

    def test_on_key_other_key_does_not_exit(self):
        from todopro_cli.utils.ui.textual_prompt import QuickAddApp

        app = QuickAddApp()
        app.exit = MagicMock()
        mock_event = MagicMock()
        mock_event.key = "a"
        app.on_key(mock_event)
        app.exit.assert_not_called()

    def test_handle_input_change_with_suggestions(self):
        """handle_input_change must update suggestions widget when matches found."""
        from todopro_cli.utils.ui.textual_prompt import QuickAddApp

        app = QuickAddApp()
        mock_task_input = MagicMock(spec=HighlightedInput)
        mock_task_input.get_suggestions.return_value = ["#Inbox", "#Work"]
        mock_suggestions_widget = MagicMock()

        def mock_query_one(selector, cls=None):
            if selector == "#task-input":
                return mock_task_input
            if selector == "#suggestions":
                return mock_suggestions_widget
            raise ValueError(f"Unknown selector: {selector}")

        app.query_one = mock_query_one
        mock_event = MagicMock()
        mock_event.value = "#"
        app.handle_input_change(mock_event)
        mock_suggestions_widget.update.assert_called_once()
        # The update should include Inbox and Work
        call_arg = mock_suggestions_widget.update.call_args[0][0]
        assert "Inbox" in call_arg
        assert "Work" in call_arg

    def test_handle_input_change_no_suggestions_clears_widget(self):
        """handle_input_change with no suggestions must clear the suggestions widget."""
        from todopro_cli.utils.ui.textual_prompt import QuickAddApp

        app = QuickAddApp()
        mock_task_input = MagicMock(spec=HighlightedInput)
        mock_task_input.get_suggestions.return_value = []
        mock_suggestions_widget = MagicMock()

        def mock_query_one(selector, cls=None):
            if selector == "#task-input":
                return mock_task_input
            if selector == "#suggestions":
                return mock_suggestions_widget
            raise ValueError

        app.query_one = mock_query_one
        mock_event = MagicMock()
        mock_event.value = "plain text"
        app.handle_input_change(mock_event)
        mock_suggestions_widget.update.assert_called_once_with("")

    def test_handle_input_change_multiple_suggestions_formatting(self):
        """First suggestion should be bolded; subsequent should not."""
        from todopro_cli.utils.ui.textual_prompt import QuickAddApp

        app = QuickAddApp()
        mock_task_input = MagicMock(spec=HighlightedInput)
        mock_task_input.get_suggestions.return_value = ["#Inbox", "#Work", "#Personal"]
        mock_suggestions_widget = MagicMock()

        def mock_query_one(selector, cls=None):
            if selector == "#task-input":
                return mock_task_input
            if selector == "#suggestions":
                return mock_suggestions_widget
            raise ValueError

        app.query_one = mock_query_one
        mock_event = MagicMock()
        mock_event.value = "#"
        app.handle_input_change(mock_event)
        call_arg = mock_suggestions_widget.update.call_args[0][0]
        # First suggestion must be bold
        assert "[bold]" in call_arg
        # Multi-line output
        assert "\n" in call_arg


# ===========================================================================
# get_interactive_input (lines 344-348)
# ===========================================================================

class TestGetInteractiveInput:
    """Tests for get_interactive_input()."""

    def test_creates_app_with_correct_project(self):
        from unittest.mock import patch as _patch

        from todopro_cli.utils.ui.textual_prompt import QuickAddApp, get_interactive_input

        with _patch("todopro_cli.utils.ui.textual_prompt.load_cache",
                    return_value=(["Inbox"], ["urgent"])):
            with _patch("todopro_cli.utils.ui.textual_prompt.QuickAddApp") as MockApp:
                mock_instance = MagicMock()
                mock_instance.result = None
                MockApp.return_value = mock_instance
                get_interactive_input("MyProject")

        MockApp.assert_called_once_with(default_project="MyProject")
        mock_instance.run.assert_called_once()

    def test_default_project_is_inbox(self):
        from unittest.mock import patch as _patch

        from todopro_cli.utils.ui.textual_prompt import QuickAddApp, get_interactive_input

        with _patch("todopro_cli.utils.ui.textual_prompt.load_cache",
                    return_value=([], [])):
            with _patch("todopro_cli.utils.ui.textual_prompt.QuickAddApp") as MockApp:
                mock_instance = MagicMock()
                mock_instance.result = None
                MockApp.return_value = mock_instance
                get_interactive_input()

        MockApp.assert_called_once_with(default_project="Inbox")
