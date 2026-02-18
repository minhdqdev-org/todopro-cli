"""Full-screen timer UI for focus mode."""

import time
from collections.abc import Callable

from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from .state import SessionState


class TimerDisplay:
    """Manages the fullscreen timer display."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def create_layout(self, session: SessionState, paused_for: int = 0) -> Layout:
        """Create the timer layout with all components."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        # Header
        if session.status == "paused":
            emoji = "⏸️ "
            title = "PAUSED"
            color = "yellow"
        elif session.status == "active":
            emoji = "🍅"
            title = "TodoPro Focus Mode"
            color = "cyan"
        else:
            emoji = "✓"
            title = "COMPLETED"
            color = "green"

        header_text = Text(f"{emoji}  {title}", style=f"bold {color}", justify="center")
        layout["header"].update(Align.center(header_text, vertical="middle"))

        # Body - main timer content
        body_content = self._create_body_content(session, paused_for)
        layout["body"].update(Align.center(body_content, vertical="middle"))

        # Footer - keyboard hints
        footer_text = self._create_footer_text(session.status)
        layout["footer"].update(Align.center(footer_text, vertical="middle"))

        return layout

    def _create_body_content(self, session: SessionState, paused_for: int) -> Group:
        """Create the main body content."""
        components = []

        # Task title
        if session.task_title:
            task_text = Text(
                session.task_title[:50], style="bold white", justify="center"
            )
            if session.task_id:
                task_id_short = session.task_id[:8]
                task_text.append(f" (#{task_id_short})", style="dim")
            components.append(task_text)
            components.append(Text(""))  # Spacer

        # Timer countdown
        remaining = session.time_remaining()
        if remaining < 0:
            remaining = 0

        mins = remaining // 60
        secs = remaining % 60

        if session.status == "paused":
            timer_color = "yellow"
        elif remaining < 60:
            timer_color = "red"
        elif remaining < 300:
            timer_color = "yellow"
        else:
            timer_color = "cyan"

        timer_text = Text(
            f"{mins:02d}:{secs:02d}", style=f"bold {timer_color}", justify="center"
        )
        timer_text.stylize("bold", 0, len(timer_text))

        # Make it bigger by duplicating
        big_timer = Text(justify="center")
        big_timer.append(" " * 10)
        big_timer.append(timer_text.plain, style=timer_color)
        big_timer.append(" " * 10)

        components.append(big_timer)
        components.append(Text(""))  # Spacer

        # Progress bar
        total_seconds = session.duration_minutes * 60
        elapsed = total_seconds - remaining
        progress_pct = (
            min(100, int((elapsed / total_seconds) * 100)) if total_seconds > 0 else 0
        )

        # Create progress bar manually
        bar_width = 40
        filled = int(bar_width * progress_pct / 100)
        empty = bar_width - filled
        progress_bar = "▓" * filled + "░" * empty

        progress_text = Text(justify="center")
        progress_text.append(progress_bar + f"  {progress_pct}%", style="dim")
        components.append(progress_text)

        # Additional info if paused
        if session.status == "paused" and paused_for > 0:
            components.append(Text(""))  # Spacer
            paused_mins = paused_for // 60
            paused_secs = paused_for % 60
            paused_text = Text(
                f"Paused for: {paused_mins:02d}:{paused_secs:02d}",
                style="yellow dim",
                justify="center",
            )
            components.append(paused_text)

        return Group(*components)

    def _create_footer_text(self, status: str) -> Text:
        """Create footer with keyboard hints."""
        if status == "paused":
            hints = "Press 'r' to resume  •  'q' to quit  •  's' to stop"
        else:
            hints = "Press 'p' to pause  •  'q' to quit  •  's' to stop"

        return Text(hints, style="dim", justify="center")

    def run_timer(
        self,
        session: SessionState,
        on_pause: Callable[[], None] | None = None,
        on_resume: Callable[[], None] | None = None,
        on_stop: Callable[[], None] | None = None,
        on_complete: Callable[[], None] | None = None,
    ) -> str:
        """
        Run the fullscreen timer.

        Returns the final status: 'completed', 'stopped', or 'interrupted'.
        """
        from .keyboard import KeyboardHandler

        keyboard = KeyboardHandler()
        paused_since = None
        last_status = session.status

        try:
            with Live(
                self.create_layout(session, 0),
                console=self.console,
                refresh_per_second=4,
                screen=True,
            ) as live:
                while True:
                    # Check keyboard input
                    key = keyboard.get_key()

                    if key == "p" and session.status == "active":
                        # Pause
                        session.status = "paused"
                        paused_since = time.time()
                        if on_pause:
                            on_pause()

                    elif key == "r" and session.status == "paused":
                        # Resume
                        if paused_since:
                            paused_duration = int(time.time() - paused_since)
                            session.accumulated_paused_seconds += paused_duration
                        session.status = "active"
                        paused_since = None
                        if on_resume:
                            on_resume()

                    elif key in ("q", "s"):
                        # Quit or stop
                        if on_stop:
                            on_stop()
                        return "stopped"

                    # Calculate paused duration
                    paused_for = 0
                    if session.status == "paused" and paused_since:
                        paused_for = int(time.time() - paused_since)

                    # Check if timer expired
                    remaining = session.time_remaining()
                    if remaining <= 0 and session.status == "active":
                        session.status = "completed"
                        if on_complete:
                            on_complete()
                        # Show completion for 2 seconds
                        live.update(self.create_layout(session, paused_for))
                        time.sleep(2)
                        return "completed"

                    # Update display
                    live.update(self.create_layout(session, paused_for))
                    time.sleep(0.25)

        except KeyboardInterrupt:
            return "interrupted"
        finally:
            keyboard.stop()


def show_completion_message(session: SessionState, console: Console | None = None):
    """Show a completion message after timer ends."""
    console = console or Console()

    actual_minutes = (
        session.duration_minutes * 60 - session.accumulated_paused_seconds
    ) // 60

    panel = Panel(
        f"""[bold green]🎉 Focus Session Complete![/bold green]

Task: {session.task_title or "N/A"}
Duration: {session.duration_minutes} minutes
Actual focus time: {actual_minutes} minutes

Session saved to history.""",
        border_style="green",
        padding=(1, 2),
    )

    console.print(panel)


def show_stopped_message(session: SessionState, console: Console | None = None):
    """Show a message when session is stopped early."""
    console = console or Console()

    total_seconds = session.duration_minutes * 60
    remaining = session.time_remaining()
    elapsed = total_seconds - remaining
    elapsed_minutes = elapsed // 60

    panel = Panel(
        f"""[yellow]Session Stopped[/yellow]

Task: {session.task_title or "N/A"}
Time focused: {elapsed_minutes} minutes
Remaining: {remaining // 60} minutes

Partial session saved to history.""",
        border_style="yellow",
        padding=(1, 2),
    )

    console.print(panel)
