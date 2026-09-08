from enum import Enum, auto

from playwright.sync_api import sync_playwright
from rich.text import Text
from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, HorizontalGroup, Vertical, VerticalScroll
from textual.coordinate import Coordinate
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    RichLog,
)
from typing_extensions import Any, cast

from database import (
    close,
    connect,
    get_jobs_for_display,
    init_tables,
    mark_job_applied,
    mark_job_discarded,
)
from pipeline import load_config, load_filters
from scrapers.linkedin import linkedin_scraper
from scrapers.scraper_utilities import JobEntry, JobFilters, JobStatus


class ScraperSources(Enum):
    LINKEDIN = auto()

def truncate_text(value: str, width: int) -> Text:
    text = Text(value)
    text.truncate(width, overflow="ellipsis")
    return text

COLUMNS = (
    ("Title", "title", 50),
    ("Company", "company", 30),
    ("Description", "description", 30),
    ("Score", "score", 10),
    ("Status", "status", 20),
)

SCRAPERS = {
    ScraperSources.LINKEDIN: linkedin_scraper,
}

"""
# ===================== #
#        Layer 0
# ===================== #
"""

class MainApp(App): # pyright: ignore[reportMissingTypeArgument]
    TITLE = "CareerLens"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("s", "expand_scrape_screen", "Scrape jobs"),
        Binding("b", "browse_jobs", "Browse jobs"),
        Binding("d", "toggle_dark", "Toggle theme"),
    ]
    CSS_PATH = "css/MainApp.css"

    def __init__(self) -> None:
        super().__init__()
        self.config: dict[str, object] = load_config()
        self.filters: JobFilters = load_filters(self.config)

    def compose(self) -> ComposeResult:
        yield Header(show_clock = True)
        yield Footer()
        with Vertical(id="menu"), Vertical(id="buttons"):
            yield Button("Scrape Jobs", id="scrape")
            yield Button("Browse Jobs", id="browse")

    def action_expand_scrape_screen(self) -> None:
        _ = self.push_screen(ScrapeMenu())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "scrape":
            self.action_expand_scrape_screen()

    def on_shutdown(self) -> None:
        ...

    """
        linkedin_scraper(conn, browser, config, filters)
    
    # TODO: deduplicate_staging()
    drain_staging(conn, config)"""

"""
# ===================== #
#        Layer 1
# ===================== #
"""

class ScrapeMenu(Screen): # pyright: ignore[reportMissingTypeArgument]
    CSS_PATH = "css/ScrapeMenu.css"

    def __init__(self):
        super().__init__()
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock = True)
        yield Footer()
        with Vertical(id="menu"), Vertical(id="buttons"):
            yield Button("Scrape LinkedIn", id="scrape-linkedin")
            yield Button("Return", id="return")

    def dismiss_scrape_screen(self) -> None:
        _ = self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "return":
            self.dismiss_scrape_screen()
        if event.button.id == "scrape-linkedin":
            _ = self.app.push_screen(ScrapeWebsites([ScraperSources.LINKEDIN]))

"""
# ===================== #
#        Layer 2
# ===================== #
"""

class ScrapeWebsites(Screen): # pyright: ignore[reportMissingTypeArgument]
    #CSS_PATH = "css/ScrapeLinkedin.css"
    def __init__(self, scraper_sources: list[ScraperSources]) -> None:
        super().__init__()
        self.scraper_sources: list[ScraperSources] = scraper_sources
        self.scrape_complete: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock = True)
        yield RichLog(id = "log")
        yield Footer()
        yield Button("Test", id="sneed")

    def dismiss_scrape_linkedin_screen(self) -> None:
        _ = self.dismiss()

    def on_mount(self) -> None:
        self.run_scraper()

    def write_log(self, message: Text) -> None:
        log = self.query_one("#log", RichLog)
        _ = log.write(message)

    def on_key(self, event: events.Key) -> None:
        if self.scrape_complete:
            _ = event.stop()
            self.dismiss_scrape_linkedin_screen()
    
    @work(thread=True)
    def run_scraper(self) -> None:
        # TODO: implement a way to quit halfway through with a button, ^q, and ^c
        app = cast(MainApp, self.app)   # basedpyright workaround

        def progress_callback(message: Text) -> None:
            self.app.call_from_thread(self.write_log, message)

        conn = connect()
        try:
            init_tables(conn)

            with sync_playwright() as p:
                browser = p.firefox.launch(headless = True)
                for source in self.scraper_sources:
                    s = SCRAPERS[source]
                    s(conn, app.config, app.filters, browser, progress_callback)

        finally:
            close(conn)
            self.scrape_complete = True
            self.write_log(Text("Press any key to continue...", style = "#f52bfb"))



"""
# ===================== #
#        Layer Unsorted
# ===================== #
"""

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
            if job.status is not None and job.status.value == JobStatus.DISCARDED.value:
                row_key = self.table.coordinate_to_cell_key(Coordinate(row, 0)).row_key
                self.query_one("#debug", Label).update(f"Block reached, row {row}")
                self.table.remove_row(row_key)
                self.jobs.pop(row)
            else:
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
        Binding("d", "discard_entry", "Discard"),
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

    def __init__(self, job: JobEntry, conn) -> None:
        super().__init__()
        self.job = job
        self.conn = conn

    def compose(self) -> ComposeResult:
        md = f"""
## {self.job.title or "No title"}

**{self.job.company or "No company"}** · {self.job.location or "No location"}

Status: {self.job.status.value if self.job.status is not None else "No status"}\n
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

{"Created at: " + str(self.job.created_at) if self.job.created_at else ""}

{"Updated at: " + str(self.job.updated_at) if self.job.updated_at else ""}

{"Applied at: " + str(self.job.applied_at) if self.job.applied_at else ""}
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

    def discard_prompt_finished(self, reason: str | None) -> None:
        if reason:
            self.job.discard_reason = reason
            self.job.status = JobStatus.DISCARDED
            mark_job_discarded(self.conn, self.job)
            self.dismiss(self.job)

    def action_close_job_view(self) -> None:
        self.dismiss()

    def action_open_apply_view(self) -> None:
        if self.job.status == JobStatus.PENDING_MANUAL_REVIEW:
            self.app.push_screen(ResumePrompt(), callback = self.resume_prompt_finished)

    def action_discard_entry(self) -> None:
        self.app.push_screen(DiscardPrompt(), callback = self.discard_prompt_finished)


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

class DiscardPrompt(ModalScreen): # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [
        Binding("escape", "exit_view", "Cancel"),
    ]
    
    CSS = """
    DiscardPrompt {
        align: center middle;
    }
    
    #discard-prompt {
        width: 70%;
        height: auto;
        padding: 2;
        border: round $accent;
        background: $surface;
    }
    
    #disacrd-prompt Input {
        margin: 1 0;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Vertical(id="discard-prompt"):
            yield Label("Why is this job being discarded?")
            yield Input(placeholder="e.g. Rejected", id="discard-input")

    def on_mount(self) -> None:
        self.query_one("#discard-input", Input).focus()
    
    def action_exit_view(self) -> None:
        self.dismiss()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)