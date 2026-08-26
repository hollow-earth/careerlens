from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Label, Static, Markdown

from database import close, connect, get_jobs_for_display

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

    def compose(self) -> ComposeResult:
        yield Footer()
        yield DataTable()

    def on_mount(self) -> None:
        conn = connect()
        table = self.query_one(DataTable)
        for header, _, width in COLUMNS:
            table.add_column(header, width=width)
        self.jobs = get_jobs_for_display(conn)

        _ = table.add_rows([
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
        close(conn)

    def action_expand_job_view(self) -> None:
            table = self.query_one(DataTable)
            if table.cursor_row < 0:
                return
            job = self.jobs[table.cursor_row]    
            self.push_screen(ExpandedJobView(job))

class ExpandedJobView(ModalScreen): # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [
        Binding("escape", "close_job_view", "Close entry"),
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

    def __init__(self, job) -> None:
        super().__init__()
        self.job = job

    def compose(self) -> ComposeResult:
        yield Footer()
        
        with VerticalScroll(id="job-view"):
            yield Markdown(self.create_markdown())

    def action_close_job_view(self) -> None:
        self.dismiss()

    def create_markdown(self) -> str:
        return f"""
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