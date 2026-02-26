"""Comprehensive unit tests for board_view.py.

Covers TaskViewModel, SectionViewModel, BoardViewApp initialization,
data structures, current-section resolution, and navigation logic.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from todopro_cli.utils.ui.board_view import (
    AddTaskButton,
    BoardViewApp,
    Section,
    SectionSeparator,
    SectionTitle,
    SectionViewModel,
    TaskCard,
    TaskCheckbox,
    TaskViewModel,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task_data(id_: str, content: str, *, due_date=None, is_completed=False):
    return {"id": id_, "content": content, "due_date": due_date, "is_completed": is_completed}


def _make_app(*task_ids, contents=None):
    """Build a BoardViewApp with N tasks in the default (no) section."""
    contents = contents or [f"Task {i}" for i in range(len(task_ids))]
    tasks = [_task_data(tid, c) for tid, c in zip(task_ids, contents)]
    return BoardViewApp(project_code="inbox", tasks_list=tasks)


def _add_section(app: BoardViewApp, section_id: str, *, tasks: list[str] | None = None) -> SectionViewModel:
    """Inject a second (mocked) section into an existing app."""
    display_order = len(app.sections)
    sv = SectionViewModel(id=section_id, name=f"Section {display_order}", display_order=display_order)
    app.sections.append(sv)

    for idx, task_content in enumerate(tasks or []):
        tid = f"{section_id}_t{idx}"
        tv = TaskViewModel(
            id=tid,
            content=task_content,
            display_order=idx,
            section=sv,
        )
        sv.tasks.append(tv)
        tc = TaskCard(tv)
        app.task_card_map[tid] = tc

    # Wire a mock section component so query calls don't blow up
    mock_sc = MagicMock(spec=Section)
    mock_sc.model = sv
    mock_sc.query_exactly_one.side_effect = lambda cls: (
        next(
            (app.task_card_map[t.id] for t in sv.tasks if cls is TaskCard),
            AddTaskButton(sv),
        )
        if cls is not AddTaskButton
        else AddTaskButton(sv)
    )
    mock_sc.query_one.return_value = SectionTitle(sv)
    mock_sc.get_right_separator.return_value = None
    app.section_component_map[section_id] = mock_sc
    return sv


# ===========================================================================
# TaskViewModel
# ===========================================================================

class TestTaskViewModel:
    """Unit tests for TaskViewModel data class."""

    def test_init_defaults(self):
        vm = TaskViewModel(id="t1", content="Buy milk")
        assert vm.id == "t1"
        assert vm.content == "Buy milk"
        assert vm.due_date is None
        assert vm.display_order == 0
        assert vm.section is None
        assert vm.is_completed is False

    def test_init_all_fields(self):
        sec = SectionViewModel(id="s1", name="S1")
        vm = TaskViewModel(
            id="t2",
            content="Deploy app",
            due_date="2024-12-31",
            display_order=7,
            section=sec,
            is_completed=True,
        )
        assert vm.due_date == "2024-12-31"
        assert vm.display_order == 7
        assert vm.section is sec
        assert vm.is_completed is True

    def test_get_section_returns_bound_section(self):
        sec = SectionViewModel(id="s1", name="S1")
        vm = TaskViewModel(id="t1", content="Task", section=sec)
        assert vm.get_section() is sec

    def test_get_section_asserts_when_none(self):
        vm = TaskViewModel(id="t1", content="Task")
        with pytest.raises(AssertionError):
            vm.get_section()

    def test_id_is_string(self):
        vm = TaskViewModel(id="abc-123", content="x")
        assert isinstance(vm.id, str)


# ===========================================================================
# SectionViewModel
# ===========================================================================

class TestSectionViewModel:
    """Unit tests for SectionViewModel data class."""

    def test_init_defaults(self):
        sm = SectionViewModel(id="s1", name="Backlog")
        assert sm.id == "s1"
        assert sm.name == "Backlog"
        assert sm.display_order == 0
        assert sm.tasks == []

    def test_init_with_explicit_fields(self):
        tasks = [TaskViewModel(id=f"t{i}", content=f"T{i}") for i in range(3)]
        sm = SectionViewModel(id="s2", name="Sprint", display_order=2, tasks=tasks)
        assert sm.display_order == 2
        assert len(sm.tasks) == 3

    def test_tasks_defaults_are_independent(self):
        """Two sections should not share the same list object."""
        s1 = SectionViewModel(id="s1", name="A")
        s2 = SectionViewModel(id="s2", name="B")
        s1.tasks.append(TaskViewModel(id="t1", content="x"))
        assert len(s2.tasks) == 0


# ===========================================================================
# BoardViewApp — initialisation
# ===========================================================================

class TestBoardViewAppInit:
    """Tests for BoardViewApp.__init__ and _init_data."""

    def test_empty_task_list_creates_one_section(self):
        app = BoardViewApp(project_code="inbox", tasks_list=[])
        assert len(app.sections) == 1
        assert app.sections[0].id == ""
        assert app.sections[0].name == "(No section)"

    def test_project_code_stored(self):
        app = BoardViewApp(project_code="myproject", tasks_list=[])
        assert app.project_code == "myproject"

    def test_initial_mode_is_normal(self):
        app = BoardViewApp(project_code="p", tasks_list=[])
        assert app.mode == "normal"

    def test_no_selected_component_when_empty(self):
        app = BoardViewApp(project_code="p", tasks_list=[])
        assert app.selected_component is None

    def test_task_cards_created_for_each_task(self):
        app = _make_app("t1", "t2", "t3")
        assert set(app.task_card_map.keys()) == {"t1", "t2", "t3"}

    def test_selected_component_is_first_task_card(self):
        app = _make_app("t1", "t2")
        assert app.selected_component is app.task_card_map["t1"]

    def test_last_display_order_is_zero_after_init(self):
        app = _make_app("t1", "t2")
        assert app.last_display_order == 0

    def test_tasks_assigned_ascending_display_orders(self):
        app = _make_app("a", "b", "c")
        tasks = app.sections[0].tasks
        assert [t.display_order for t in tasks] == [0, 1, 2]

    def test_tasks_assigned_to_no_section(self):
        app = _make_app("t1", "t2")
        no_sec = app.sections[0]
        for task in no_sec.tasks:
            assert task.section is no_sec

    def test_section_component_map_keyed_by_section_id(self):
        app = _make_app("t1")
        assert "" in app.section_component_map

    def test_due_date_parsed_to_date_string(self):
        tasks = [{"id": "t1", "content": "T", "due_date": "2024-06-15T12:00:00Z", "is_completed": False}]
        app = BoardViewApp(project_code="p", tasks_list=tasks)
        assert app.sections[0].tasks[0].due_date == "2024-06-15"

    def test_null_due_date_stays_none(self):
        tasks = [{"id": "t1", "content": "T", "due_date": None, "is_completed": False}]
        app = BoardViewApp(project_code="p", tasks_list=tasks)
        assert app.sections[0].tasks[0].due_date is None

    def test_is_completed_flag_preserved(self):
        tasks = [{"id": "t1", "content": "T", "due_date": None, "is_completed": True}]
        app = BoardViewApp(project_code="p", tasks_list=tasks)
        assert app.sections[0].tasks[0].is_completed is True

    def test_task_card_models_match_view_models(self):
        app = _make_app("t1", "t2")
        for tid, card in app.task_card_map.items():
            assert card.model.id == tid


# ===========================================================================
# BoardViewApp — mode switching
# ===========================================================================

class TestBoardViewAppMode:
    """Tests for switch_mode."""

    def test_switch_mode_changes_attribute(self):
        app = BoardViewApp(project_code="p", tasks_list=[])
        app.switch_mode("insert")
        assert app.mode == "insert"

    def test_switch_mode_back_to_normal(self):
        app = BoardViewApp(project_code="p", tasks_list=[])
        app.switch_mode("edit-section-s1")
        app.switch_mode("normal")
        assert app.mode == "normal"

    def test_log_debug_noop_when_debug_false(self):
        """log_debug must not raise even without a running app."""
        app = BoardViewApp(project_code="p", tasks_list=[])
        # Should complete silently (DEBUG=False in source)
        app.log_debug("some debug message")


# ===========================================================================
# BoardViewApp — get_current_section
# ===========================================================================

class TestGetCurrentSection:
    """Tests for get_current_section()."""

    def setup_method(self):
        self.app = _make_app("t1", "t2")

    def test_returns_section_when_task_card_selected(self):
        self.app.selected_component = self.app.task_card_map["t1"]
        sec = self.app.get_current_section()
        assert sec is self.app.sections[0]

    def test_returns_section_when_add_task_button_selected(self):
        btn = AddTaskButton(self.app.sections[0])
        self.app.selected_component = btn
        sec = self.app.get_current_section()
        assert sec is self.app.sections[0]

    def test_returns_left_section_when_separator_selected(self):
        left_sec = self.app.sections[0]
        sep = SectionSeparator("vertical", left_section=left_sec)
        self.app.selected_component = sep
        sec = self.app.get_current_section()
        assert sec is left_sec

    def test_returns_model_when_section_title_selected(self):
        title = SectionTitle(self.app.sections[0])
        self.app.selected_component = title
        sec = self.app.get_current_section()
        assert sec is self.app.sections[0]

    def test_raises_when_selected_is_none(self):
        self.app.selected_component = None
        with pytest.raises((ValueError, AttributeError, TypeError)):
            self.app.get_current_section()


# ===========================================================================
# BoardViewApp — get_section_component_by_order
# ===========================================================================

class TestGetSectionComponentByOrder:
    """Tests for get_section_component_by_order."""

    def test_returns_section_for_index_zero(self):
        app = _make_app("t1")
        comp = app.get_section_component_by_order(0)
        assert comp is app.section_component_map[""]

    def test_returns_correct_component_for_second_section(self):
        app = _make_app("t1")
        _add_section(app, "s2", tasks=["Task A"])
        comp = app.get_section_component_by_order(1)
        assert comp is app.section_component_map["s2"]


# ===========================================================================
# BoardViewApp — get_below_component
# ===========================================================================

class TestGetBelowComponent:
    """Tests for get_below_component()."""

    def test_task_to_next_task_in_same_section(self):
        app = _make_app("t1", "t2", "t3")
        app.selected_component = app.task_card_map["t1"]
        below = app.get_below_component(app.task_card_map["t1"])
        assert below is app.task_card_map["t2"]

    def test_second_task_goes_to_third(self):
        app = _make_app("t1", "t2", "t3")
        app.selected_component = app.task_card_map["t2"]
        below = app.get_below_component(app.task_card_map["t2"])
        assert below is app.task_card_map["t3"]

    def test_last_task_yields_add_task_button(self):
        app = _make_app("t1", "t2")
        app.selected_component = app.task_card_map["t2"]
        # Patch section component so query_exactly_one works
        add_btn = AddTaskButton(app.sections[0])
        mock_sc = MagicMock()
        mock_sc.query_exactly_one.return_value = add_btn
        app.section_component_map[""] = mock_sc
        below = app.get_below_component(app.task_card_map["t2"])
        assert isinstance(below, AddTaskButton)

    def test_returns_none_for_none_input(self):
        app = BoardViewApp(project_code="p", tasks_list=[])
        assert app.get_below_component(None) is None

    def test_section_title_with_tasks_goes_to_first_task(self):
        app = _make_app("t1", "t2")
        title = SectionTitle(app.sections[0])
        app.selected_component = title
        below = app.get_below_component(title)
        assert below is app.task_card_map["t1"]

    def test_section_title_with_no_tasks_goes_to_add_button(self):
        app = BoardViewApp(project_code="p", tasks_list=[])
        title = SectionTitle(app.sections[0])
        app.selected_component = title
        add_btn = AddTaskButton(app.sections[0])
        mock_sc = MagicMock()
        mock_sc.query_exactly_one.return_value = add_btn
        app.section_component_map[""] = mock_sc
        below = app.get_below_component(title)
        assert isinstance(below, AddTaskButton)


# ===========================================================================
# BoardViewApp — get_above_component
# ===========================================================================

class TestGetAboveComponent:
    """Tests for get_above_component()."""

    def test_task_goes_to_previous_task(self):
        app = _make_app("t1", "t2", "t3")
        app.selected_component = app.task_card_map["t2"]
        above = app.get_above_component(app.task_card_map["t2"])
        assert above is app.task_card_map["t1"]

    def test_third_task_goes_to_second(self):
        app = _make_app("t1", "t2", "t3")
        app.selected_component = app.task_card_map["t3"]
        above = app.get_above_component(app.task_card_map["t3"])
        assert above is app.task_card_map["t2"]

    def test_first_task_goes_to_section_title(self):
        app = _make_app("t1", "t2")
        app.selected_component = app.task_card_map["t1"]
        title = SectionTitle(app.sections[0])
        mock_sc = MagicMock()
        mock_sc.query_one.return_value = title
        app.section_component_map[""] = mock_sc
        above = app.get_above_component(app.task_card_map["t1"])
        assert isinstance(above, SectionTitle)

    def test_add_task_button_last_task_above(self):
        app = _make_app("t1", "t2")
        btn = AddTaskButton(app.sections[0])
        app.selected_component = btn
        above = app.get_above_component(btn)
        assert above is app.task_card_map["t2"]

    def test_add_task_button_with_empty_section_goes_to_title(self):
        app = BoardViewApp(project_code="p", tasks_list=[])
        btn = AddTaskButton(app.sections[0])
        app.selected_component = btn
        title = SectionTitle(app.sections[0])
        mock_sc = MagicMock()
        mock_sc.query_one.return_value = title
        app.section_component_map[""] = mock_sc
        above = app.get_above_component(btn)
        assert isinstance(above, SectionTitle)

    def test_returns_none_for_none_input(self):
        app = BoardViewApp(project_code="p", tasks_list=[])
        assert app.get_above_component(None) is None


# ===========================================================================
# BoardViewApp — get_next_component (horizontal navigation)
# ===========================================================================

class TestGetNextComponent:
    """Tests for get_next_component()."""

    def test_returns_none_when_single_section_task_card(self):
        app = _make_app("t1")
        app.selected_component = app.task_card_map["t1"]
        assert app.get_next_component(app.task_card_map["t1"]) is None

    def test_returns_none_when_single_section_add_button(self):
        app = _make_app("t1")
        btn = AddTaskButton(app.sections[0])
        app.selected_component = btn
        assert app.get_next_component(btn) is None

    def test_task_card_navigates_to_next_section_task(self):
        """From a task card in section-0, move right to aligned task in section-1."""
        app = _make_app("t0", "t1")
        _add_section(app, "s2", tasks=["S2 Task 0", "S2 Task 1"])
        app.selected_component = app.task_card_map["t0"]
        app.last_display_order = 0
        nxt = app.get_next_component(app.task_card_map["t0"])
        assert nxt is app.task_card_map["s2_t0"]

    def test_add_button_navigates_to_next_section_task(self):
        app = _make_app("t0")
        _add_section(app, "s2", tasks=["S2-T0"])
        btn = AddTaskButton(app.sections[0])
        app.selected_component = btn
        app.last_display_order = 0
        nxt = app.get_next_component(btn)
        assert nxt is app.task_card_map["s2_t0"]

    def test_section_title_returns_none_when_last_section(self):
        app = _make_app("t1")
        title = SectionTitle(app.sections[0])
        app.selected_component = title
        result = app.get_next_component(title)
        assert result is None


# ===========================================================================
# BoardViewApp — get_previous_component (horizontal navigation)
# ===========================================================================

class TestGetPreviousComponent:
    """Tests for get_previous_component()."""

    def test_returns_none_when_first_section_task_card(self):
        app = _make_app("t1")
        app.selected_component = app.task_card_map["t1"]
        assert app.get_previous_component(app.task_card_map["t1"]) is None

    def test_returns_none_when_first_section_add_button(self):
        app = _make_app("t1")
        btn = AddTaskButton(app.sections[0])
        app.selected_component = btn
        assert app.get_previous_component(btn) is None

    def test_second_section_task_card_navigates_back(self):
        """From task in section-1, move left to aligned task in section-0."""
        app = _make_app("t0", "t1")
        s2 = _add_section(app, "s2", tasks=["S2 Task 0"])
        tc_s2 = app.task_card_map["s2_t0"]
        app.selected_component = tc_s2
        app.last_display_order = 0
        prev = app.get_previous_component(tc_s2)
        assert prev is app.task_card_map["t0"]

    def test_separator_navigates_to_left_section_title(self):
        app = _make_app("t1")
        left_sec = app.sections[0]
        sep = SectionSeparator("vertical", left_section=left_sec)
        app.selected_component = sep
        title = SectionTitle(left_sec)
        mock_sc = MagicMock()
        mock_sc.query_one.return_value = title
        app.section_component_map[""] = mock_sc
        prev = app.get_previous_component(sep)
        assert isinstance(prev, SectionTitle)

    def test_section_title_returns_none_when_first(self):
        app = _make_app("t1")
        title = SectionTitle(app.sections[0])
        app.selected_component = title
        result = app.get_previous_component(title)
        assert result is None


# ===========================================================================
# TaskCheckbox
# ===========================================================================

class TestTaskCheckbox:
    """Tests for TaskCheckbox widget logic."""

    def _make_checkbox(self, completed=False) -> TaskCheckbox:
        vm = TaskViewModel(id="t1", content="Task", is_completed=completed)
        return TaskCheckbox(vm)

    def test_initial_state_unchecked(self):
        cb = self._make_checkbox(completed=False)
        assert cb.checked is False

    def test_initial_state_checked(self):
        cb = self._make_checkbox(completed=True)
        assert cb.checked is True

    def test_on_click_toggles_checked(self):
        cb = self._make_checkbox(completed=False)
        cb.on_click()
        assert cb.checked is True

    def test_double_click_restores_state(self):
        cb = self._make_checkbox(completed=False)
        cb.on_click()
        cb.on_click()
        assert cb.checked is False

    def test_update_checkbox_unchecked_symbol(self):
        """update_checkbox must update static text - no crash when called."""
        cb = self._make_checkbox(completed=False)
        # Should not raise; the renderable is updated internally
        cb.update_checkbox()

    def test_update_checkbox_checked_symbol(self):
        cb = self._make_checkbox(completed=True)
        cb.update_checkbox()  # Must not raise


# ===========================================================================
# SectionTitle (pure-Python portions)
# ===========================================================================

class TestSectionTitleInit:
    """Tests for SectionTitle initialisation."""

    def test_init_sets_model(self):
        sv = SectionViewModel(id="s1", name="My Section")
        title = SectionTitle(sv)
        assert title.model is sv

    def test_initial_mode_is_view(self):
        sv = SectionViewModel(id="s1", name="My Section")
        title = SectionTitle(sv)
        assert title.mode == "view"


# ===========================================================================
# AddTaskButton (pure-Python portions)
# ===========================================================================

class TestAddTaskButton:
    """Tests for AddTaskButton initialisation."""

    def test_display_order_equals_section_task_count(self):
        sv = SectionViewModel(id="s1", name="S", tasks=[
            TaskViewModel(id=f"t{i}", content=f"T{i}") for i in range(3)
        ])
        btn = AddTaskButton(sv)
        assert btn.display_order == 3

    def test_empty_section_display_order_is_zero(self):
        sv = SectionViewModel(id="s1", name="S")
        btn = AddTaskButton(sv)
        assert btn.display_order == 0

    def test_section_reference_stored(self):
        sv = SectionViewModel(id="s1", name="S")
        btn = AddTaskButton(sv)
        assert btn.section is sv


# ===========================================================================
# SectionSeparator
# ===========================================================================

class TestSectionSeparator:
    """Tests for SectionSeparator initialisation."""

    def test_left_section_stored(self):
        sv = SectionViewModel(id="s1", name="S1")
        sep = SectionSeparator("vertical", left_section=sv)
        assert sep.left_section is sv

    def test_none_left_section(self):
        sep = SectionSeparator("vertical", left_section=None)
        assert sep.left_section is None

    def test_on_click_returns_none(self):
        """SectionSeparator.on_click must always return without side effects."""
        sep = SectionSeparator("vertical", left_section=None)
        mock_event = MagicMock()
        result = sep.on_click(mock_event)
        assert result is None


# ===========================================================================
# TaskCardContainer — init (pure-Python portions)
# ===========================================================================

class TestTaskCardContainerInit:
    """Tests for TaskCardContainer constructor."""

    def test_model_assigned(self):
        vm = TaskViewModel(id="t1", content="My task", due_date="2024-06-01")
        from todopro_cli.utils.ui.board_view import TaskCardContainer
        tc = TaskCardContainer(vm)
        assert tc.model is vm

    def test_model_stores_due_date(self):
        vm = TaskViewModel(id="t2", content="Another", due_date="2024-12-31")
        from todopro_cli.utils.ui.board_view import TaskCardContainer
        tc = TaskCardContainer(vm)
        assert tc.model.due_date == "2024-12-31"


# ===========================================================================
# BoardViewApp — go_to_component
# ===========================================================================

class TestGoToComponent:
    """Tests for go_to_component()."""

    def _goto(self, app, component):
        """Call go_to_component with query_one patched to avoid ScreenStackError."""
        from textual.css.query import QueryError
        from unittest.mock import patch as _patch
        with _patch.object(app, "query_one", side_effect=QueryError("suppressed")):
            app.go_to_component(component)

    def test_task_card_sets_selected_component(self):
        app = _make_app("t1", "t2")
        app.selected_component = None
        tc = app.task_card_map["t1"]
        self._goto(app, tc)
        assert app.selected_component is tc

    def test_task_card_updates_last_display_order(self):
        app = _make_app("t1", "t2")
        self._goto(app, app.task_card_map["t2"])
        assert app.last_display_order == 1

    def test_add_task_button_updates_last_display_order(self):
        app = _make_app("t1", "t2")
        btn = AddTaskButton(app.sections[0])
        self._goto(app, btn)
        assert app.last_display_order == btn.display_order

    def test_section_title_resets_display_order_to_zero(self):
        app = _make_app("t1", "t2")
        app.last_display_order = 5
        title = SectionTitle(app.sections[0])
        self._goto(app, title)
        assert app.last_display_order == 0

    def test_separator_gets_highlighted_separator_class(self):
        app = _make_app("t1")
        app.selected_component = None
        sep = SectionSeparator("vertical", left_section=app.sections[0])
        self._goto(app, sep)
        assert "highlighted-separator" in sep.classes

    def test_section_title_gets_highlighted_section_title_class(self):
        app = _make_app("t1")
        app.selected_component = None
        title = SectionTitle(app.sections[0])
        self._goto(app, title)
        assert "highlighted-section-title" in title.classes

    def test_task_card_gets_highlighted_class(self):
        app = _make_app("t1")
        app.selected_component = None
        tc = app.task_card_map["t1"]
        self._goto(app, tc)
        assert "highlighted" in tc.classes

    def test_previous_separator_class_removed(self):
        app = _make_app("t1")
        sep = SectionSeparator("vertical", left_section=app.sections[0])
        sep.add_class("highlighted-separator")
        app.selected_component = sep
        tc = app.task_card_map["t1"]
        self._goto(app, tc)
        assert "highlighted-separator" not in sep.classes

    def test_previous_section_title_class_removed(self):
        app = _make_app("t1")
        title = SectionTitle(app.sections[0])
        title.add_class("highlighted-section-title")
        app.selected_component = title
        tc = app.task_card_map["t1"]
        self._goto(app, tc)
        assert "highlighted-section-title" not in title.classes

    def test_previous_task_card_highlighted_class_removed(self):
        app = _make_app("t1", "t2")
        tc1 = app.task_card_map["t1"]
        tc1.add_class("highlighted")
        app.selected_component = tc1
        tc2 = app.task_card_map["t2"]
        self._goto(app, tc2)
        assert "highlighted" not in tc1.classes

    def test_none_previous_component_no_crash(self):
        app = _make_app("t1")
        app.selected_component = None
        tc = app.task_card_map["t1"]
        self._goto(app, tc)  # Must not raise
        assert app.selected_component is tc


# ===========================================================================
# BoardViewApp — SectionTitle.enter_edit_mode edge case
# ===========================================================================

class TestSectionTitleEnterEditMode:
    """Tests for SectionTitle.enter_edit_mode()."""

    def test_enter_edit_mode_empty_id_returns_early(self):
        """When section id is empty string, enter_edit_mode must return without switching modes."""
        sv = SectionViewModel(id="", name="(No section)")
        title = SectionTitle(sv)
        mock_event = MagicMock()
        # Must not raise or switch mode
        title.enter_edit_mode(mock_event)
        # mode stays 'view'
        assert title.mode == "view"

    def test_enter_edit_mode_already_edit_does_nothing(self):
        """Already in edit mode → enter_edit_mode does nothing."""
        sv = SectionViewModel(id="s1", name="Sprint")
        title = SectionTitle(sv)
        title.mode = "edit"
        mock_event = MagicMock()
        title.enter_edit_mode(mock_event)
        assert title.mode == "edit"  # unchanged


# ===========================================================================
# BoardViewApp — get_next_component (SectionSeparator path, line 446-457)
# ===========================================================================

class TestGetNextComponentSeparator:
    """Tests for SectionSeparator navigation in get_next_component."""

    def test_separator_returns_right_section_title(self):
        app = _make_app("t0")
        _add_section(app, "s2", tasks=["S2-T0"])
        # Separator left_section = no_section (display_order=0)
        # right_section = s2 (display_order=1)
        sep = SectionSeparator("vertical", left_section=app.sections[0])
        app.selected_component = sep
        nxt = app.get_next_component(sep)
        assert isinstance(nxt, SectionTitle)

    def test_separator_with_last_left_section_returns_none(self):
        """Separator whose left_section is the last section → None."""
        app = _make_app("t0")
        s2 = _add_section(app, "s2")
        # s2 is last (display_order=1 = len-1), so right_section=None
        sep = SectionSeparator("vertical", left_section=s2)
        app.selected_component = sep
        nxt = app.get_next_component(sep)
        assert nxt is None


# ===========================================================================
# BoardViewApp — get_next_component (SectionTitle path, lines 483-486)
# ===========================================================================

class TestGetNextComponentSectionTitle:
    """Tests for SectionTitle navigation in get_next_component."""

    def test_section_title_returns_right_separator(self):
        app = _make_app("t0")
        _add_section(app, "s2", tasks=["S2-T0"])
        title = SectionTitle(app.sections[0])
        app.selected_component = title

        sep = SectionSeparator("vertical", left_section=app.sections[0])
        mock_sc = MagicMock()
        mock_sc.model = app.sections[0]
        mock_sc.get_right_separator.return_value = sep
        app.section_component_map[""] = mock_sc

        nxt = app.get_next_component(title)
        assert nxt is sep

    def test_section_title_last_section_returns_none(self):
        """SectionTitle in the last section → None."""
        app = _make_app("t1")
        title = SectionTitle(app.sections[0])
        app.selected_component = title
        assert app.get_next_component(title) is None


# ===========================================================================
# BoardViewApp — get_next_component (AddTaskButton/TaskCard empty next section)
# ===========================================================================

class TestGetNextComponentEmptyNextSection:
    """Tests for navigation when next section has no tasks."""

    def test_add_button_next_section_empty_returns_add_button(self):
        app = _make_app("t0")
        _add_section(app, "s2")  # empty section
        btn = AddTaskButton(app.sections[0])
        app.selected_component = btn
        add_btn_s2 = AddTaskButton(app.sections[1])
        app.section_component_map["s2"].query_exactly_one.return_value = add_btn_s2
        nxt = app.get_next_component(btn)
        assert isinstance(nxt, AddTaskButton)

    def test_task_card_next_section_empty_returns_add_button(self):
        app = _make_app("t0")
        _add_section(app, "s2")  # empty
        tc = app.task_card_map["t0"]
        app.selected_component = tc
        add_btn_s2 = AddTaskButton(app.sections[1])
        app.section_component_map["s2"].query_exactly_one.return_value = add_btn_s2
        nxt = app.get_next_component(tc)
        assert isinstance(nxt, AddTaskButton)

    def test_task_card_last_display_order_exceeds_next_section(self):
        """last_display_order >= len(next_section.tasks) → AddTaskButton."""
        app = _make_app("t0", "t1", "t2")  # 3 tasks in no_section
        _add_section(app, "s2", tasks=["S2-T0"])  # only 1 task
        tc = app.task_card_map["t0"]
        app.selected_component = tc
        app.last_display_order = 2  # >= len(s2.tasks)=1
        add_btn_s2 = AddTaskButton(app.sections[1])
        app.section_component_map["s2"].query_exactly_one.return_value = add_btn_s2
        nxt = app.get_next_component(tc)
        assert isinstance(nxt, AddTaskButton)


# ===========================================================================
# BoardViewApp — get_previous_component (SectionTitle path, lines 520-523)
# ===========================================================================

class TestGetPreviousComponentSectionTitle:
    """Tests for SectionTitle navigation in get_previous_component."""

    def test_section_title_in_second_section_returns_separator(self):
        app = _make_app("t0")
        s2 = _add_section(app, "s2", tasks=["S2-T0"])
        title = SectionTitle(s2)
        app.selected_component = title

        sep = SectionSeparator("vertical", left_section=app.sections[0])
        mock_sc = MagicMock()
        mock_sc.model = app.sections[0]
        mock_sc.get_right_separator.return_value = sep
        app.section_component_map[""] = mock_sc

        prev = app.get_previous_component(title)
        assert prev is sep

    def test_section_title_in_first_section_returns_none(self):
        app = _make_app("t1")
        title = SectionTitle(app.sections[0])
        app.selected_component = title
        assert app.get_previous_component(title) is None


# ===========================================================================
# BoardViewApp — get_previous_component (empty left section, line 505)
# ===========================================================================

class TestGetPreviousComponentEmptyLeft:
    """Tests for navigation when left section has no tasks."""

    def test_task_card_previous_left_section_empty(self):
        app = _make_app()  # empty no-section
        s2 = _add_section(app, "s2", tasks=["S2-T0"])
        tc_s2 = app.task_card_map["s2_t0"]
        app.selected_component = tc_s2
        add_btn = AddTaskButton(app.sections[0])
        mock_sc = MagicMock()
        mock_sc.query_exactly_one.return_value = add_btn
        app.section_component_map[""] = mock_sc
        prev = app.get_previous_component(tc_s2)
        assert isinstance(prev, AddTaskButton)

    def test_add_button_previous_left_section_empty(self):
        app = _make_app()  # empty no-section
        s2 = _add_section(app, "s2", tasks=["S2-T0"])
        btn = AddTaskButton(s2)
        app.selected_component = btn
        add_btn_no_sec = AddTaskButton(app.sections[0])
        mock_sc = MagicMock()
        mock_sc.query_exactly_one.return_value = add_btn_no_sec
        app.section_component_map[""] = mock_sc
        prev = app.get_previous_component(btn)
        assert isinstance(prev, AddTaskButton)


# ===========================================================================
# BoardViewApp — get_above_component (SectionSeparator, lines 548-561)
# ===========================================================================

class TestGetAboveComponentSeparator:
    """Tests for SectionSeparator navigation in get_above_component."""

    def test_separator_above_with_tasks_in_right_section(self):
        app = _make_app("t0")
        _add_section(app, "s2", tasks=["S2-T0"])
        left_sec = app.sections[0]
        sep = SectionSeparator("vertical", left_section=left_sec)
        app.selected_component = sep
        app.last_display_order = 0
        above = app.get_above_component(sep)
        assert above is app.task_card_map["s2_t0"]

    def test_separator_above_right_section_empty(self):
        app = _make_app("t0")
        s2 = _add_section(app, "s2")  # empty
        sep = SectionSeparator("vertical", left_section=app.sections[0])
        app.selected_component = sep
        add_btn = AddTaskButton(s2)
        app.section_component_map["s2"].query_exactly_one.return_value = add_btn
        above = app.get_above_component(sep)
        assert isinstance(above, AddTaskButton)

    def test_separator_above_last_display_order_exceeds_right_tasks(self):
        """last_display_order >= len(right_section.tasks) → AddTaskButton."""
        app = _make_app("t0")
        _add_section(app, "s2", tasks=["S2-T0"])  # 1 task
        sep = SectionSeparator("vertical", left_section=app.sections[0])
        app.selected_component = sep
        app.last_display_order = 5  # >= 1
        add_btn = AddTaskButton(app.sections[1])
        app.section_component_map["s2"].query_exactly_one.return_value = add_btn
        above = app.get_above_component(sep)
        assert isinstance(above, AddTaskButton)


# ===========================================================================
# BoardViewApp — get_below_component (SectionSeparator, lines 579-589)
# ===========================================================================

class TestGetBelowComponentSeparator:
    """Tests for SectionSeparator navigation in get_below_component."""

    def test_separator_below_with_tasks_in_left_section(self):
        app = _make_app("t0")
        _add_section(app, "s2", tasks=["S2-T0"])
        left_sec = app.sections[0]
        sep = SectionSeparator("vertical", left_section=left_sec)
        app.selected_component = sep
        app.last_display_order = 0
        below = app.get_below_component(sep)
        assert below is app.task_card_map["t0"]

    def test_separator_below_left_section_empty(self):
        app = _make_app()  # empty no-section
        _add_section(app, "s2", tasks=["S2-T0"])
        sep = SectionSeparator("vertical", left_section=app.sections[0])
        app.selected_component = sep
        add_btn = AddTaskButton(app.sections[0])
        mock_sc = MagicMock()
        mock_sc.query_exactly_one.return_value = add_btn
        app.section_component_map[""] = mock_sc
        below = app.get_below_component(sep)
        assert isinstance(below, AddTaskButton)

    def test_separator_below_last_display_order_exceeds_left_tasks(self):
        """last_display_order >= len(left_section.tasks) → AddTaskButton."""
        app = _make_app("t0")
        _add_section(app, "s2", tasks=["S2-T0"])
        sep = SectionSeparator("vertical", left_section=app.sections[0])
        app.selected_component = sep
        app.last_display_order = 5  # >= 1 task in no_section
        add_btn = AddTaskButton(app.sections[0])
        mock_sc = MagicMock()
        mock_sc.query_exactly_one.return_value = add_btn
        app.section_component_map[""] = mock_sc
        below = app.get_below_component(sep)
        assert isinstance(below, AddTaskButton)

    def test_get_below_unknown_widget_type_returns_none(self):
        """get_below_component returns None for widgets not explicitly handled."""
        app = _make_app("t1")
        mock_widget = MagicMock()  # Not a TaskCard/SectionSeparator/SectionTitle
        result = app.get_below_component(mock_widget)
        assert result is None


# ===========================================================================
# BoardViewApp — on_key (normal mode)
# ===========================================================================

class TestOnKeyNormalMode:
    """Tests for on_key() in normal mode."""

    def test_down_navigates_to_next_task(self):
        app = _make_app("t1", "t2")
        app.selected_component = app.task_card_map["t1"]
        mock_event = MagicMock()
        mock_event.key = "down"

        from unittest.mock import patch as _patch
        with _patch.object(app, "go_to_component") as mock_go:
            app.on_key(mock_event)
        mock_go.assert_called_once_with(app.task_card_map["t2"])
        mock_event.stop.assert_called_once()

    def test_j_navigates_down(self):
        app = _make_app("t1", "t2")
        app.selected_component = app.task_card_map["t1"]
        mock_event = MagicMock()
        mock_event.key = "j"

        from unittest.mock import patch as _patch
        with _patch.object(app, "go_to_component") as mock_go:
            app.on_key(mock_event)
        mock_go.assert_called_once()

    def test_up_navigates_to_prev_task(self):
        app = _make_app("t1", "t2")
        app.selected_component = app.task_card_map["t2"]
        mock_event = MagicMock()
        mock_event.key = "up"

        from unittest.mock import patch as _patch
        with _patch.object(app, "go_to_component") as mock_go:
            app.on_key(mock_event)
        mock_go.assert_called_once_with(app.task_card_map["t1"])

    def test_k_navigates_up(self):
        app = _make_app("t1", "t2")
        app.selected_component = app.task_card_map["t2"]
        mock_event = MagicMock()
        mock_event.key = "k"

        from unittest.mock import patch as _patch
        with _patch.object(app, "go_to_component") as mock_go:
            app.on_key(mock_event)
        mock_go.assert_called_once()

    def test_left_no_navigation_single_section(self):
        app = _make_app("t1")
        app.selected_component = app.task_card_map["t1"]
        mock_event = MagicMock()
        mock_event.key = "left"

        from unittest.mock import patch as _patch
        with _patch.object(app, "go_to_component") as mock_go:
            app.on_key(mock_event)
        mock_go.assert_not_called()

    def test_right_no_navigation_single_section(self):
        app = _make_app("t1")
        app.selected_component = app.task_card_map["t1"]
        mock_event = MagicMock()
        mock_event.key = "right"

        from unittest.mock import patch as _patch
        with _patch.object(app, "go_to_component") as mock_go:
            app.on_key(mock_event)
        mock_go.assert_not_called()

    def test_h_navigates_left(self):
        app = _make_app("t0", "t1")
        _add_section(app, "s2", tasks=["S2-T0"])
        tc_s2 = app.task_card_map["s2_t0"]
        app.selected_component = tc_s2
        app.last_display_order = 0
        mock_event = MagicMock()
        mock_event.key = "h"

        from unittest.mock import patch as _patch
        with _patch.object(app, "go_to_component") as mock_go:
            app.on_key(mock_event)
        mock_go.assert_called_once_with(app.task_card_map["t0"])

    def test_l_navigates_right(self):
        app = _make_app("t0")
        _add_section(app, "s2", tasks=["S2-T0"])
        app.selected_component = app.task_card_map["t0"]
        app.last_display_order = 0
        mock_event = MagicMock()
        mock_event.key = "l"

        from unittest.mock import patch as _patch
        with _patch.object(app, "go_to_component") as mock_go:
            app.on_key(mock_event)
        mock_go.assert_called_once()

    def test_c_toggles_checkbox_on_task_card(self):
        app = _make_app("t1")
        tc = app.task_card_map["t1"]
        app.selected_component = tc
        mock_checkbox = MagicMock()
        mock_event = MagicMock()
        mock_event.key = "c"

        from unittest.mock import patch as _patch
        with _patch.object(tc, "query_one", return_value=mock_checkbox):
            app.on_key(mock_event)
        mock_checkbox.on_click.assert_called_once()

    def test_i_enters_insert_mode(self):
        app = _make_app("t1")
        app.selected_component = app.task_card_map["t1"]
        mock_event = MagicMock()
        mock_event.key = "i"
        app.on_key(mock_event)
        assert app.mode == "insert"

    def test_enter_with_section_title_calls_enter_edit_mode(self):
        app = _make_app("t1")
        title = SectionTitle(app.sections[0])
        app.selected_component = title
        mock_event = MagicMock()
        mock_event.key = "enter"

        from unittest.mock import patch as _patch
        with _patch.object(title, "enter_edit_mode") as mock_edit:
            app.on_key(mock_event)
        mock_edit.assert_called_once_with(mock_event)

    def test_event_stop_always_called(self):
        """event.stop() must be called regardless of key pressed."""
        app = _make_app("t1")
        app.selected_component = app.task_card_map["t1"]
        mock_event = MagicMock()
        mock_event.key = "x"  # unrecognised key
        app.on_key(mock_event)
        mock_event.stop.assert_called_once()


# ===========================================================================
# BoardViewApp — on_key (edit mode)
# ===========================================================================

class TestOnKeyEditMode:
    """Tests for on_key() in edit mode."""

    def test_escape_exits_to_normal_mode(self):
        app = _make_app("t1")
        app.mode = "edit-section-s1"
        mock_event = MagicMock()
        mock_event.key = "escape"
        app.on_key(mock_event)
        assert app.mode == "normal"

    def test_enter_saves_section_title_and_resets_mode(self):
        app = _make_app("t1")
        title = SectionTitle(app.sections[0])
        app.selected_component = title
        app.mode = "edit-section-"
        mock_event = MagicMock()
        mock_event.key = "enter"

        from unittest.mock import patch as _patch
        with _patch.object(title, "save_new_name") as mock_save:
            app.on_key(mock_event)
        mock_save.assert_called_once()
        assert app.mode == "normal"

    def test_enter_no_save_when_not_section_title(self):
        """Enter in edit mode without SectionTitle selected does not crash."""
        app = _make_app("t1")
        app.selected_component = app.task_card_map["t1"]
        app.mode = "edit-section-s1"
        mock_event = MagicMock()
        mock_event.key = "enter"
        app.on_key(mock_event)  # Must not raise
        assert app.mode == "edit-section-s1"  # unchanged


# ===========================================================================
# BoardViewApp — action_toggle_dark
# ===========================================================================

class TestActionToggleDark:
    """Tests for action_toggle_dark()."""

    def test_light_to_dark(self):
        app = BoardViewApp(project_code="p", tasks_list=[])
        app.theme = "textual-light"
        app.action_toggle_dark()
        assert app.theme == "textual-dark"

    def test_dark_to_light(self):
        app = BoardViewApp(project_code="p", tasks_list=[])
        app.theme = "textual-dark"
        app.action_toggle_dark()
        assert app.theme == "textual-light"


# ===========================================================================
# run_board_view — integration with mocked services
# ===========================================================================

class TestRunBoardView:
    """Tests for run_board_view() with mocked services."""

    def test_run_board_view_calls_app_run(self):
        from unittest.mock import AsyncMock, patch as _patch, MagicMock as MM

        from todopro_cli.utils.ui.board_view import run_board_view

        mock_ctx = MM()
        mock_ctx.type = "remote"
        mock_config_svc = MM()
        mock_config_svc.get_current_context.return_value = mock_ctx

        mock_client = MM()
        mock_client.close = AsyncMock()
        mock_tasks_api = MM()
        mock_tasks_api.list_tasks = AsyncMock(return_value=[])

        with _patch("todopro_cli.services.config_service.get_config_service",
                    return_value=mock_config_svc):
            with _patch("todopro_cli.utils.ui.board_view.get_client",
                        return_value=mock_client):
                with _patch("todopro_cli.utils.ui.board_view.TasksAPI",
                            return_value=mock_tasks_api):
                    with _patch("todopro_cli.utils.ui.board_view.BoardViewApp") as MockApp:
                        mock_app_instance = MM()
                        MockApp.return_value = mock_app_instance
                        run_board_view("inbox")
                        mock_app_instance.run.assert_called_once()

    def test_run_board_view_local_context_inbox(self):
        from unittest.mock import AsyncMock, patch as _patch, MagicMock as MM

        from todopro_cli.utils.ui.board_view import run_board_view

        mock_ctx = MM()
        mock_ctx.type = "local"
        mock_config_svc = MM()
        mock_config_svc.get_current_context.return_value = mock_ctx

        mock_task = MM()
        mock_task.model_dump.return_value = {
            "id": "t1", "content": "Task", "due_date": None, "is_completed": False
        }
        mock_task_svc = MM()
        mock_task_svc.list_tasks = AsyncMock(return_value=[mock_task])

        with _patch("todopro_cli.services.config_service.get_config_service",
                    return_value=mock_config_svc):
            with _patch("todopro_cli.services.task_service.get_task_service",
                        return_value=mock_task_svc):
                with _patch("todopro_cli.utils.ui.board_view.BoardViewApp") as MockApp:
                    mock_app_instance = MM()
                    MockApp.return_value = mock_app_instance
                    run_board_view("inbox")
                    mock_app_instance.run.assert_called_once()

    def test_run_board_view_remote_dict_response(self):
        """When tasks_api returns a dict with 'tasks' key, tasks are extracted."""
        from unittest.mock import AsyncMock, patch as _patch, MagicMock as MM

        from todopro_cli.utils.ui.board_view import run_board_view

        mock_ctx = MM()
        mock_ctx.type = "remote"
        mock_config_svc = MM()
        mock_config_svc.get_current_context.return_value = mock_ctx

        mock_client = MM()
        mock_client.close = AsyncMock()
        mock_tasks_api = MM()
        mock_tasks_api.list_tasks = AsyncMock(
            return_value={"tasks": [{"id": "t1", "content": "T", "is_completed": False}]}
        )

        with _patch("todopro_cli.services.config_service.get_config_service",
                    return_value=mock_config_svc):
            with _patch("todopro_cli.utils.ui.board_view.get_client",
                        return_value=mock_client):
                with _patch("todopro_cli.utils.ui.board_view.TasksAPI",
                            return_value=mock_tasks_api):
                    with _patch("todopro_cli.utils.ui.board_view.BoardViewApp") as MockApp:
                        mock_app_instance = MM()
                        MockApp.return_value = mock_app_instance
                        run_board_view("myproject")
                        # App was created with non-empty tasks list from dict response
                        MockApp.assert_called_once()
                        args = MockApp.call_args[0]
                        assert isinstance(args[1], list)
