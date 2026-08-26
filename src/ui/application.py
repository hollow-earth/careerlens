from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.coordinate import Coordinate
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    Static,
)
from typing_extensions import Any

from database import close, connect, get_jobs_for_display, mark_job_applied
from scrapers.scraper_utilities import JobEntry, JobStatus

COLUMNS = (
    ("Title", "title", 50),
    ("Company", "company", 30),
    ("Description", "description", 30),
    ("Score", "score", 10),
    ("Status", "status", 20),
)

def truncate_text(value: str, width: int) -> Text:
    text = Text(value)
    text.truncate(width, overflow="ellipsis")
    return text

class TableApp(App): # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [
        Binding("e", "expand_job_view", "Expand entry"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.jobs = []
        self.conn = connect()
        self.table: DataTable[Any]

    def compose(self) -> ComposeResult:
        yield Footer()
        yield DataTable()

    def on_mount(self) -> None:
        self.table = self.query_one(DataTable)
        for header, key, width in COLUMNS:
            self.table.add_column(header, key=key, width=width)
        self.jobs = get_jobs_for_display(self.conn)

        _ = self.table.add_rows([
            (
                truncate_text("" if job.title is None else job.title, 50),
                truncate_text("" if job.company is None else job.company, 30),
                truncate_text("" if job.description is None else job.description, 30),
                truncate_text("" if job.score is None else str(job.score), 10),
                truncate_text("" if job.status is None else job.status.value, 20),
            ) 
            for job in self.jobs
        ])
        # TODO: add infinite scroll, it only loads the first 100 for now

    def on_shutdown(self) -> None:
        close(self.conn)

    def job_view_finished(self, job: JobEntry | None) -> None:
        if job is None:
            return
        
        row = self.table.cursor_row
        if row >= 0:
            self.table.update_cell_at(
                Coordinate(row, 4),
                truncate_text(job.status.value if job.status is not None else JobStatus.APPLIED.value, 20),
            )
        
    def action_expand_job_view(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_row < 0:
            return
        job = self.jobs[table.cursor_row]    
        self.push_screen(ExpandedJobView(job, self.conn), callback = self.job_view_finished)

class ExpandedJobView(ModalScreen): # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [
        Binding("escape", "close_job_view", "Close entry"),
        Binding("a", "open_apply_view", "Apply"),
    ]

    CSS = """
        ExpandedJobView {
            align: center middle;
        }
    
        VerticalScroll {
            width: 80%;
            height: 80%;
            border: round $accent;
            background: $surface;
            padding: 1 2;
        }

        Markdown {
            text-align: left;
        }

        MarkdownH1 {
            text-align: left;
        }
    """

    def __init__(self, job, conn) -> None:
        super().__init__()
        self.job = job
        self.conn = conn

    def compose(self) -> ComposeResult:
        md = f"""
## {self.job.title or "No title"}

**{self.job.company or "No company"}** · {self.job.location or "No location"}

Status: {self.job.status.value or "No status"}\n
{"Resume used: " + self.job.resume_used if self.job.resume_used else ""}

### Score

{self.job.short_score if self.job.short_score else "No short_score"} — **{self.job.score if self.job.score is not None else "N/A"}/100**

### Reasoning

{self.job.reasoning or "No reasoning available."}

### Description

{self.job.description or "No description available."}

### Metadata
Source: {self.job.source.value}

Job ID: {self.job.job_id}

URL: {self.job.url}

{"Created at: " + self.job.created_at if self.job.created_at else ""}

{"Updated at: " + self.job.updated_at if self.job.updated_at else ""}

{"Applied at: " + self.job.applied_at if self.job.applied_at else ""}
"""

        yield Footer()
        
        with VerticalScroll(id="job-view"):
            yield Markdown(md)

    def resume_prompt_finished(self, resume: str | None) -> None:
        if resume:
            self.job.status = JobStatus.APPLIED
            self.job.resume_used = resume
            mark_job_applied(self.conn, self.job)
            self.dismiss(self.job)

    def action_close_job_view(self) -> None:
        self.dismiss()

    def action_open_apply_view(self) -> None:
        if self.job.status == JobStatus.PENDING_MANUAL_REVIEW:
            self.app.push_screen(ResumePrompt(), callback = self.resume_prompt_finished)


class ResumePrompt(ModalScreen): # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [
        Binding("escape", "exit_view", "Cancel"),
    ]
    
    CSS = """
    ResumePrompt {
        align: center middle;
    }
    
    #resume-prompt {
        width: 70%;
        height: auto;
        padding: 2;
        border: round $accent;
        background: $surface;
    }
    
    #resume-prompt Input {
        margin: 1 0;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Vertical(id="resume-prompt"):
            yield Label("Which resume did you use?")
            yield Input(placeholder="e.g. Embedded Resume", id="resume-input")

    def on_mount(self) -> None:
        self.query_one("#resume-input", Input).focus()
    
    def action_exit_view(self) -> None:
        self.dismiss()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)