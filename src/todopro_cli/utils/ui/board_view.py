"""Textual TUI for displaying tasks in a kanban board view."""

import asyncio
import contextlib
from datetime import datetime

from textual import events
from textual.app import App, ComposeResult
from textual.containers import (
    Container,
    Horizontal,
    HorizontalScroll,
    Vertical,
    VerticalScroll,
)
from textual.css.query import QueryError
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Input, RichLog, Rule, Static

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.tasks import TasksAPI
from todopro_cli.utils.ui.console import get_console

DEBUG = False

console = get_console()


class TaskViewModel:
    """View model for a task."""

    def __init__(
        self,
        id: str,
        content: str,
        due_date: str | None = None,
        display_order: int = 0,
        section: "SectionViewModel | None" = None,
        is_completed: bool = False,
    ):
        self.id = id
        self.content = content
        self.due_date = due_date
        self.display_order = display_order
        self.section = section
        self.is_completed = is_completed

    def get_section(self) -> "SectionViewModel":
        assert self.section is not None
        return self.section


class SectionViewModel:
    """View model for a section."""

    def __init__(
        self,
        id: str,
        name: str,
        display_order: int = 0,
        tasks: list[TaskViewModel] | None = None,
    ):
        self.id = id
        self.name = name
        self.display_order = display_order
        self.tasks = tasks or []


class TaskCheckbox(Static):
    """A simple checkbox widget for tasks."""

    def __init__(self, task: TaskViewModel):
        super().__init__()
        self.model = task
        self.checked = task.is_completed
        self.update_checkbox()

    def on_click(self) -> None:
        """Toggle the checked state when clicked."""
        self.checked = not self.checked
        self.update_checkbox()

    def update_checkbox(self) -> None:
        """Update the display based on the checked state."""
        uncheck_symbol = "\u2610"
        check_symbol = "\u2611"
        checkbox_symbol = check_symbol if self.checked else uncheck_symbol
        self.update(f"{checkbox_symbol}")


class TaskCardContainer(Vertical):
    """A container for task cards."""

    app: "BoardViewApp"

    def __init__(self, task: TaskViewModel):
        super().__init__()
        self.model = task

    def compose(self) -> ComposeResult:
        yield Static(f"{self.model.content}")
        yield Static(f"\u1f4c5: {self.model.due_date or 'N/A'}")

    def on_click(self, event):
        # select the task card when clicked
        self.app.go_to_component(self.app.task_card_map[self.model.id])


class TaskCard(Horizontal):
    """A simple card to display task information."""

    def __init__(self, model: TaskViewModel):
        super().__init__()
        self.model = model
        self.add_class("task-card")

    def compose(self) -> ComposeResult:
        yield TaskCheckbox(self.model)
        yield TaskCardContainer(self.model)


class AddTaskButton(Button):
    """A button to add a new task."""

    app: "BoardViewApp"

    def __init__(self, section: SectionViewModel):
        super().__init__(label="+ Add Task", classes="add-task-button")
        self.section = section
        self.display_order = len(section.tasks)

    def on_click(self) -> None:
        """Handle the button click to add a new task."""
        self.app.log_debug(f"Add Task button clicked for section: {self.section.name}")


class SectionTitle(Container):
    """A widget to display the section title."""

    app: "BoardViewApp"

    def __init__(self, model: SectionViewModel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.mode = "view"

    def compose(self) -> ComposeResult:
        yield Static(f"[b]{self.model.name}[/b]", classes="section-name")

    def save_new_name(self):
        """Save the new section name from the input widget to the model."""
        input_widget = self.query_one(Input)
        new_name = input_widget.value.strip()

        if new_name:
            self.model.name = new_name
            self.app.log_debug(f"Section name updated to: {new_name}")
        else:
            self.app.log_debug("Section name cannot be empty. Keeping the old name.")

        self.switch_mode("view")

    def switch_mode(self, mode: str):
        """Switch between view and edit mode."""
        self.mode = mode

        if mode == "edit":
            self.query_one(Static).remove()
            input_widget = Input(
                value=self.model.name,
                classes="section-name-input",
                compact=True,
                max_length=32,
            )
            self.mount(input_widget)
            self.app.go_to_component(self)
            self.app.log_debug(f"Entered edit mode for section: {self.model.name}")
        else:
            self.query_one(Input).remove()
            section_name_static = Static(
                f"[b]{self.model.name}[/b]", classes="section-name"
            )
            self.mount(section_name_static)
            self.app.go_to_component(self)
            self.app.log_debug(f"Exited edit mode for section: {self.model.name}")

    def on_click(self, event):
        """Handle click events on the section title."""
        if event.chain == 2:
            if self.app.mode == "normal":
                self.enter_edit_mode(event)
                event.stop()
        elif event.chain == 1 and self.app.mode == "normal":
            self.app.go_to_component(self)

    def enter_edit_mode(self, event):
        """Enter edit mode when the section title is clicked and the key is Enter."""
        if self.mode == "view":
            if self.model.id == "":
                return

            self.switch_mode("edit")
            self.app.mode = f"edit-section-{self.model.id}"
            self.query_one(Input).focus()
            event.stop()


class Section(Vertical):
    """A section to group related tasks."""

    app: "BoardViewApp"

    def __init__(self, model: SectionViewModel):
        super().__init__()
        self.model = model

    def compose(self) -> ComposeResult:
        yield SectionTitle(model=self.model)
        display_list: list[TaskCard | AddTaskButton] = [
            self.app.task_card_map[task.id] for task in self.model.tasks
        ]
        display_list.append(AddTaskButton(self.model))
        yield VerticalScroll(*display_list, classes="section-tasks")

    def get_right_separator(self) -> "SectionSeparator | None":
        """Get the right separator of this section, if any."""
        for sep in self.app.query(SectionSeparator):
            if sep.left_section is not None and sep.left_section.id == self.model.id:
                return sep
        return None


class SectionSeparator(Rule):
    """A separator between sections that can also be selected."""

    def __init__(self, *args, left_section: SectionViewModel | None, **kwargs):
        super().__init__(*args, **kwargs)
        self.left_section = left_section

    def on_click(self, event):
        return


class Body(HorizontalScroll):
    """The main body of the app."""

    app: "BoardViewApp"

    def compose(self) -> ComposeResult:
        sections = list(self.app.section_component_map.values())

        if len(sections) == 0:
            return

        yield sections[0]
        for i in range(1, len(sections)):
            yield SectionSeparator("vertical", left_section=sections[i - 1].model)
            yield sections[i]

    def on_resize(self, _: events.Resize) -> None:
        """Handle resize events to adjust layout if necessary."""
        if self.app.size.width < 80:
            section_width = self.app.size.width - 4
        elif self.app.size.width < 120:
            section_width = (self.app.size.width - 4) // 2
        else:
            section_width = (self.app.size.width - 4) // 4

        for section in self.query(Section):
            section.styles.width = section_width

    def on_click(self, event):
        if self.app.mode.startswith("edit"):
            if isinstance(self.app.selected_component, Input):
                self.app.selected_component.blur()
            self.app.mode = "normal"


class BoardViewApp(App):
    """A Textual app for displaying tasks in a kanban board view."""

    TITLE = "TodoPro - Board View"
    CSS_PATH = "board_view.tcss"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit the app"),
    ]

    def __init__(
        self,
        project_code: str,
        tasks_list: list | None = None,
    ):
        super().__init__()
        self.project_code = project_code
        self.mode = "normal"

        self.tasks: list[TaskViewModel] = []
        self.task_card_map: dict[str, TaskCard] = {}
        self.sections: list[SectionViewModel] = []
        self.section_component_map: dict[str, Section] = {}

        self.selected_component: Widget | None = None
        self.last_display_order = 0
        self._data_loaded = False

        # Initialize data before UI composition
        self._init_data(tasks_list or [])

    def _init_data(self, tasks_list: list):
        """Initialize the data structures synchronously."""
        # Create a default "No section" for tasks without sections
        no_section = SectionViewModel(
            id="", name="(No section)", display_order=0, tasks=[]
        )
        self.sections.append(no_section)

        # Convert API tasks to view models
        for idx, task_data in enumerate(tasks_list):
            # Format due date
            due_date = None
            if task_data.get("due_date"):
                try:
                    dt = datetime.fromisoformat(
                        task_data["due_date"].replace("Z", "+00:00")
                    )
                    due_date = dt.strftime("%Y-%m-%d")
                except Exception:
                    due_date = task_data.get("due_date")

            task = TaskViewModel(
                id=task_data["id"],
                content=task_data["content"],
                due_date=due_date,
                display_order=idx,
                section=no_section,
                is_completed=task_data.get("is_completed", False),
            )

            no_section.tasks.append(task)
            task_card = TaskCard(task)
            self.task_card_map[task.id] = task_card

        # Create section component
        no_section_component = Section(no_section)
        self.section_component_map[no_section.id] = no_section_component

        # Set initial selected component
        if len(no_section.tasks) > 0:
            self.selected_component = self.task_card_map[no_section.tasks[0].id]
            self.last_display_order = 0

    def on_mount(self) -> None:
        """Called when app starts."""
        # Highlight the initially selected component
        if self.selected_component:
            self.go_to_component(self.selected_component)

    def go_to_component(
        self,
        component: TaskCard | SectionSeparator | AddTaskButton | SectionTitle | Input,
    ):
        """Highlight the selected component."""
        if self.selected_component is not None:
            if isinstance(self.selected_component, SectionSeparator):
                self.selected_component.remove_class("highlighted-separator")
            elif isinstance(self.selected_component, SectionTitle):
                self.selected_component.remove_class("highlighted-section-title")
            else:
                self.selected_component.remove_class("highlighted")

        self.selected_component = component

        if isinstance(self.selected_component, SectionSeparator):
            self.selected_component.add_class("highlighted-separator")
        elif isinstance(self.selected_component, SectionTitle):
            self.selected_component.add_class("highlighted-section-title")
        else:
            self.selected_component.add_class("highlighted")

        if isinstance(component, TaskCard):
            self.last_display_order = component.model.display_order
        elif isinstance(component, AddTaskButton):
            self.last_display_order = component.display_order
        elif isinstance(component, SectionTitle):
            self.last_display_order = 0

        with contextlib.suppress(QueryError):
            self.app.query_one(Body).scroll_to_widget(component, immediate=True)

        if isinstance(component, TaskCard):
            self.log_debug(
                f"{component} - {component.model.get_section().name} - {component.model.content}"
            )
        elif isinstance(component, SectionSeparator):
            self.log_debug(
                f"Section Separator - left section: {component.left_section.name if component.left_section else 'N/A'}"
            )
        elif isinstance(component, AddTaskButton):
            self.log_debug(f"Add Task Button - section: {component.section.name}")

    def get_current_section(self) -> SectionViewModel:
        """Get the current section based on the selected component."""
        if isinstance(self.selected_component, TaskCard):
            section = self.selected_component.model.section
            assert section is not None
            return section
        if isinstance(self.selected_component, AddTaskButton):
            return self.selected_component.section
        if isinstance(self.selected_component, SectionSeparator):
            assert self.selected_component.left_section is not None
            return self.selected_component.left_section
        if isinstance(self.selected_component, SectionTitle):
            return self.selected_component.model
        raise ValueError("No component selected")

    def get_section_component_by_order(self, display_order: int) -> Section:
        """Get the section component by its display order."""
        return self.section_component_map[self.sections[display_order].id]

    def get_next_component(
        self, component: Widget | None
    ) -> TaskCard | SectionSeparator | AddTaskButton | SectionTitle | None:
        """Get the next component in the navigation order."""
        if isinstance(component, AddTaskButton):
            next_section = (
                self.sections[component.section.display_order + 1]
                if component.section.display_order < len(self.sections) - 1
                else None
            )

            if next_section is None:
                return None
            if len(next_section.tasks) == 0 or self.last_display_order >= len(
                next_section.tasks
            ):
                return self.section_component_map[next_section.id].query_exactly_one(
                    AddTaskButton
                )
            next_task = next_section.tasks[self.last_display_order]
            return self.task_card_map[next_task.id]

        if isinstance(component, SectionSeparator):
            assert component.left_section is not None
            right_section = (
                self.sections[component.left_section.display_order + 1]
                if component.left_section.display_order < len(self.sections) - 1
                else None
            )
            if right_section is None:
                return None
            right_section_component = self.get_section_component_by_order(
                component.left_section.display_order + 1
            )
            return right_section_component.query_one(SectionTitle)

        if isinstance(component, TaskCard):
            current_section = component.model.section
            assert current_section is not None
            next_section = (
                self.sections[current_section.display_order + 1]
                if current_section.display_order < len(self.sections) - 1
                else None
            )

            if next_section is None:
                return None
            if len(next_section.tasks) == 0 or self.last_display_order >= len(
                next_section.tasks
            ):
                return self.section_component_map[next_section.id].query_exactly_one(
                    AddTaskButton
                )
            next_task = next_section.tasks[self.last_display_order]
            return self.task_card_map[next_task.id]

        if isinstance(component, SectionTitle):
            current_section = self.get_current_section()
            if current_section.display_order == len(self.sections) - 1:
                return None
            return self.get_section_component_by_order(
                current_section.display_order
            ).get_right_separator()
        return None

    def get_previous_component(
        self, component: Widget | None
    ) -> TaskCard | SectionSeparator | AddTaskButton | SectionTitle | None:
        """Get the previous component in the navigation order."""
        if isinstance(component, (AddTaskButton, TaskCard)):
            current_section = (
                component.model.section
                if isinstance(component, TaskCard)
                else component.section
            )
            assert current_section is not None
            if current_section.display_order == 0:
                return None
            left_section = self.sections[current_section.display_order - 1]
            if len(left_section.tasks) == 0 or self.last_display_order >= len(
                left_section.tasks
            ):
                return self.section_component_map[left_section.id].query_exactly_one(
                    AddTaskButton
                )
            previous_task = left_section.tasks[self.last_display_order]
            return self.task_card_map[previous_task.id]
        if isinstance(component, SectionSeparator):
            assert component.left_section is not None
            left_section_component = self.get_section_component_by_order(
                component.left_section.display_order
            )
            return left_section_component.query_one(SectionTitle)
        if isinstance(component, SectionTitle):
            current_section = self.get_current_section()
            if current_section.display_order == 0:
                return None
            return self.get_section_component_by_order(
                current_section.display_order - 1
            ).get_right_separator()
        return None

    def get_above_component(
        self, component: Widget | None
    ) -> TaskCard | SectionSeparator | AddTaskButton | SectionTitle | None:
        """Get the component above the given component in the navigation order."""
        if component is None:
            return None

        if isinstance(component, AddTaskButton):
            section = component.section
            if len(section.tasks) == 0:
                section_component = self.section_component_map[section.id]
                return section_component.query_one(SectionTitle)

            return self.task_card_map[section.tasks[-1].id]
        if isinstance(component, TaskCard):
            current_section_model = self.get_current_section()
            if component.model.display_order > 0:
                previous_task = current_section_model.tasks[
                    component.model.display_order - 1
                ]
                return self.task_card_map[previous_task.id]
            section_component = self.section_component_map[current_section_model.id]
            return section_component.query_one(SectionTitle)
        if isinstance(component, SectionSeparator):
            assert component.left_section is not None
            right_section = self.sections[component.left_section.display_order + 1]

            if len(right_section.tasks) == 0 or self.last_display_order >= len(
                right_section.tasks
            ):
                return self.section_component_map[right_section.id].query_exactly_one(
                    AddTaskButton
                )
            next_task = right_section.tasks[self.last_display_order]
            return self.task_card_map[next_task.id]

        return None

    def get_below_component(
        self, component: Widget | None
    ) -> TaskCard | SectionSeparator | AddTaskButton | SectionTitle | None:
        """Get the component below the given component in the navigation order."""
        if component is None:
            return None

        if isinstance(component, TaskCard):
            current_section_model = self.get_current_section()
            current_section = self.section_component_map[current_section_model.id]

            if component.model.display_order == len(current_section_model.tasks) - 1:
                return current_section.query_exactly_one(AddTaskButton)
            next_task = current_section_model.tasks[component.model.display_order + 1]
            return self.task_card_map[next_task.id]
        if isinstance(component, SectionSeparator):
            assert component.left_section is not None
            left_section = self.sections[component.left_section.display_order]

            if len(left_section.tasks) == 0 or self.last_display_order >= len(
                left_section.tasks
            ):
                return self.section_component_map[left_section.id].query_exactly_one(
                    AddTaskButton
                )
            previous_task = left_section.tasks[self.last_display_order]
            return self.task_card_map[previous_task.id]
        if isinstance(component, SectionTitle):
            section = self.get_current_section()
            if len(section.tasks) == 0:
                return self.section_component_map[section.id].query_exactly_one(
                    AddTaskButton
                )
            first_task = section.tasks[0]
            return self.task_card_map[first_task.id]
        return None

    def log_debug(self, message: str) -> None:
        """Log debug messages to RichLog."""
        if not DEBUG:
            return

        with contextlib.suppress(QueryError):
            self.app.query_one(RichLog).write(f"DEBUG: {message}")

    def on_key(self, event: events.Key):
        """Handle key events for navigation."""
        self.log_debug(
            f"Key pressed: {event.key} - Current mode: {self.mode} - Selected component: {self.selected_component}"
        )

        if self.mode == "normal":
            match event.key:
                case "left" | "h":
                    component = self.get_previous_component(self.selected_component)
                    if component is not None:
                        self.go_to_component(component)
                case "right" | "l":
                    component = self.get_next_component(self.selected_component)
                    if component is not None:
                        self.go_to_component(component)
                case "up" | "k":
                    component = self.get_above_component(self.selected_component)
                    if component is not None:
                        self.go_to_component(component)
                case "down" | "j":
                    component = self.get_below_component(self.selected_component)
                    if component is not None:
                        self.go_to_component(component)
                case "c":
                    if isinstance(self.selected_component, TaskCard):
                        checkbox = self.selected_component.query_one(TaskCheckbox)
                        checkbox.on_click()
                case "i":
                    self.mode = "insert"
                    self.log_debug("Entered insert mode")
                case "enter":
                    if isinstance(self.selected_component, SectionTitle):
                        self.selected_component.enter_edit_mode(event)
        elif self.mode.startswith("edit"):
            match event.key:
                case "escape":
                    self.mode = "normal"
                    self.log_debug("Exited insert mode")
                case "enter":
                    if isinstance(self.selected_component, SectionTitle):
                        self.selected_component.save_new_name()
                        self.mode = "normal"

        event.stop()

    def compose(self) -> ComposeResult:
        yield Header()
        if DEBUG:
            yield RichLog()
        yield Body()
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )


def run_board_view(project_code: str):
    """Run the board view app."""
    from todopro_cli.services.config_service import get_config_service

    config_svc = get_config_service()
    current_context = config_svc.get_current_context()

    async def preload_data():
        """Preload task data before app starts."""
        if current_context.type == "local":
            from todopro_cli.services.task_service import TaskService

            storage_strategy_context = get_storage_strategy_context()
            task_service = TaskService(storage_strategy_context.task_repository)

            if project_code.lower() == "inbox":
                tasks = await task_service.list_tasks(status="active")
            else:
                tasks = await task_service.list_tasks(project_id=project_code)

            return [t.model_dump() for t in tasks]
        client = get_client()
        tasks_api = TasksAPI(client)

        try:
            if project_code.lower() == "inbox":
                tasks_data = await tasks_api.list_tasks()
            else:
                tasks_data = await tasks_api.list_tasks(project_id=project_code)

            # Handle both list and dict responses
            if isinstance(tasks_data, dict):
                return tasks_data.get("tasks", [])
            return tasks_data
        finally:
            await client.close()

    # Load tasks before starting the app
    tasks_list = asyncio.run(preload_data())

    app = BoardViewApp(project_code, tasks_list)
    app.run()
