from enum import Enum, auto
from pathlib import Path

from playwright.sync_api import sync_playwright
from rich.text import Text
from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, HorizontalGroup, Vertical, VerticalScroll
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
    Static,
)
from typing import Any, cast

from database import (
    close,
    connect,
    get_jobs_for_display,
    init_tables,
    mark_job_applied,
    mark_job_discarded,
)
from pipeline import load_config, load_filters, drain_staging
from scrapers.linkedin import linkedin_scraper
from scrapers.scraper_utilities import JobEntry, JobFilters, JobStatus


class ScraperSources(Enum):
    LINKEDIN = auto()

# TODO: remove this soon, redundant function but there's still old code that depends on it
def truncate_text(value: str, width: int) -> Text:
    text = Text(value)
    text.truncate(width, overflow="ellipsis")
    return text

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
        Binding(".", "toggle_dark", "Toggle theme"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config: dict[str, object] = load_config()
        self.filters: JobFilters = load_filters(self.config)

    def on_mount(self) -> None:
        self.push_screen(MainMenu())

    def on_shutdown(self) -> None:
        ...

    """
    # TODO: deduplicate_staging()
    drain_staging(conn, config)"""

"""
# ===================== #
#        Layer 1
# ===================== #
"""
ASCII_TITLE = """   ___                          __                
 / __\\__ _ _ __ ___  ___ _ __ / /  ___ _ __  ___ 
/ /  / _` | '__/ _ \\/ _ \\ '__/ /  / _ \\ '_ \\/ __|
/ /__| (_| | | |  __/  __/ | / /__|  __/ | | \\__ \\
\\____/\\__,_|_|  \\___|\\___|_| \\____/\\___|_| |_|___/"""

class MainMenu(Screen): # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [
        Binding("p", "expand_process_screen", "Process jobs"),
        Binding("b", "expand_jobs_screen", "Browse jobs"),
    ]
    CSS_PATH = "css/MainMenu.tcss"
    
    def __init__(self) -> None:
        super().__init__()
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock = True)
        
        with Container(id="menu"):
            yield Static(ASCII_TITLE, id = "title")
            
            with Vertical(id="buttons"):
                yield Button("Process Jobs", id="process-jobs")
                yield Button("Browse Jobs", id="browse-jobs")

        yield Footer()

    def action_expand_process_screen(self) -> None:
        _ = self.app.push_screen(ProcessingMenu())

    def action_expand_jobs_screen(self) -> None:
        _ = self.app.push_screen(JobTable())
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "process-jobs":
            self.action_expand_process_screen()
        if event.button.id == "browse-jobs":
            self.action_expand_jobs_screen()

"""
# ===================== #
#        Layer 2
# ===================== #
"""

class ProcessingMenu(Screen): # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [
        Binding("l", "scrape_linkedin", "Scrape LinkedIn"),
        Binding("d", "drain_staging", "Drain Staging"),
        Binding("escape", "exit_view", "Cancel"),
    ]
    CSS_PATH = "css/ScrapeMenu.tcss"

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header(show_clock = True)
        yield Footer()
        with Vertical(id="menu"), Vertical(id="buttons"):
            yield Button("Scrape LinkedIn", id="scrape-linkedin")
            yield Button("Drain Staging", id="drain-staging")
            yield Button("Return", id="return")

    def action_scrape_linkedin(self) -> None:
        _ = self.app.push_screen(ScrapeWebsites([ScraperSources.LINKEDIN]))

    # TODO: replace this at some point; break up pipeline.drain_staging into different functions
    def action_drain_staging(self) -> None:
        _ = self.app.push_screen(DrainStaging())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "return":
            _ = self.dismiss()
        if event.button.id == "scrape-linkedin":
            _ = self.app.push_screen(ScrapeWebsites([ScraperSources.LINKEDIN]))
        if event.button.id == "drain-staging":
            _ = self.action_drain_staging()

    def action_exit_view(self) -> None:
        _ = self.dismiss()

class JobTable(Screen): # pyright: ignore[reportMissingTypeArgument]
    COLUMNS = (
        ("Title", "title", 50),
        ("Company", "company", 30),
        ("Description", "description", 30),
        ("Score", "score", 10),
        ("Status", "status", 20),
    )
    
    BINDINGS = [
        Binding("e", "expand_job_view", "Expand entry"),
        Binding("escape", "exit_view", "Cancel"),
    ]
    
    def __init__(self) -> None:
        super().__init__()
        self.jobs = []
        self.conn = connect()
        self.table: DataTable[object]

    def compose(self) -> ComposeResult:
        yield Header(show_clock = True)
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        self.table = self.query_one(DataTable)
        self.jobs = get_jobs_for_display(self.conn)
        for header, key, width in self.COLUMNS:
            _ = self.table.add_column(header, key=key, width=width)
        _ = self.table.add_rows(
            (
                "" if job.title is None else job.title,
                "" if job.company is None else job.company,
                "" if job.description is None else job.description,
                "" if job.score is None else str(job.score),
                "" if job.status is None else job.status.value,
            ) 
            for job in self.jobs
        )
        # TODO: add infinite scroll, it only loads the first 100 for now

    def action_exit_view(self) -> None:
        _ = self.dismiss()
    
    def on_shutdown(self) -> None:
        close(self.conn)

    def update_table(self, job: JobEntry | None) -> None:
        if job is None:
            return

        # Consider replacing with row = self.jobs.index(job) which is O(n) or using a key for each row
        row = self.table.cursor_row
        if job.job_id != self.jobs[row].job_id or job.url != self.jobs[row].url:
            row = self.jobs.index(job)

        if row < 0 or job.status is None:
            return
        elif job.status.value == JobStatus.DISCARDED.value:
            row_key = self.table.coordinate_to_cell_key(Coordinate(row, 0)).row_key
            self.table.remove_row(row_key)
            _ = self.jobs.pop(row)
        elif job.status.value == JobStatus.APPLIED.value:
            self.table.update_cell_at(Coordinate(row, 4), job.status.value)

    def action_expand_job_view(self) -> None:
        row = self.query_one(DataTable).cursor_row
        if row < 0:
            return
        job = self.jobs[row]    
        _ = self.app.push_screen(ExpandedJobView(job, self.conn), self.update_table)

"""
# ===================== #
#        Layer 3
# ===================== #
"""

class ExpandedJobView(ModalScreen): # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [
        Binding("escape", "close_job_view", "Close entry"),
        Binding("a", "open_apply_view", "Apply"),
        Binding("d", "discard_entry", "Discard"),
    ]
    CSS_PATH = "css/ExpandedJobView.tcss"

    def __init__(self, job: JobEntry, conn) -> None:
        super().__init__()
        self.job = job
        self.conn = conn

    def compose(self) -> ComposeResult:
        template = Path("./src/ui/md/ExpandedJobView.md").read_text()
        md = template.format(
            title       = self.job.title or "Missing title", 
            company     = self.job.company or "Missing company",
            location    = self.job.location or "Missing location",
            status      = self.job.status.value if self.job.status else "Missing status",
            resume_used = f"Resume used: {self.job.resume_used}" if self.job.resume_used else "",
            short_score = self.job.short_score or "No short_score",
            score       = self.job.score if self.job.score is not None else "N/A",
            reasoning   = self.job.reasoning or "No reasoning available.",
            description = self.job.description or "No description available.",
            source      = self.job.source.value,
            job_id      = self.job.job_id,
            url         = self.job.url,
            created_at  = f"Created at: {self.job.created_at}" if self.job.created_at else "",
            updated_at  = f"Updated at: {self.job.updated_at}" if self.job.updated_at else "",
            applied_at  = f"Applied at: {self.job.applied_at}" if self.job.applied_at else "",
        )
        with VerticalScroll(id="job-view"):
            yield Markdown(md)
        yield Footer()

    def apply_prompt_finished(self, resume: str | None) -> None:
        if resume:
            self.job.status = JobStatus.APPLIED
            self.job.resume_used = resume
            mark_job_applied(self.conn, self.job)
            _ = self.dismiss(self.job)

    def discard_prompt_finished(self, reason: str | None) -> None:
        if reason:
            self.job.status = JobStatus.DISCARDED
            self.job.discard_reason = reason
            mark_job_discarded(self.conn, self.job)
            _ = self.dismiss(self.job)

    def action_open_apply_view(self) -> None:
        if self.job.status == JobStatus.PENDING_MANUAL_REVIEW:
            self.app.push_screen(ApplyPrompt(), self.apply_prompt_finished)

    def action_discard_entry(self) -> None:
        self.app.push_screen(DiscardPrompt(), callback = self.discard_prompt_finished)

    def action_close_job_view(self) -> None:
        self.dismiss()

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

class DrainStaging(Screen): # pyright: ignore[reportMissingTypeArgument]
    #CSS_PATH = "css/ScrapeLinkedin.css"
    def __init__(self) -> None:
        super().__init__()
        self.drain_staging_complete: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock = True)
        yield RichLog(id = "log")
        yield Footer()
        yield Button("Test", id="sneed")

    def on_mount(self) -> None:
        self.run_drain_staging()

    def write_log(self, message: Text) -> None:
        log = self.query_one("#log", RichLog)
        _ = log.write(message)

    def on_key(self, event: events.Key) -> None:
        if self.drain_staging_complete:
            _ = event.stop()
            _ = self.dismiss()
    
    @work(thread=True)
    def run_drain_staging(self) -> None:
        # TODO: implement a way to quit halfway through with a button, ^q, and ^c
        app = cast(MainApp, self.app)   # basedpyright workaround

        def progress_callback(message: Text) -> None:
            self.app.call_from_thread(self.write_log, message)

        conn = connect()
        try:
            init_tables(conn)
            drain_staging(conn, app.config, progress_callback)

        finally:
            close(conn)
            self.drain_staging_complete = True
            self.write_log(Text("Press any key to continue...", style = "#f52bfb"))

"""
# ===================== #
#        Layer 4
# ===================== #
"""

class ApplyPrompt(ModalScreen): # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [
        Binding("escape", "exit_view", "Cancel"),
    ]

    CSS_PATH = "css/ApplyPrompt.tcss"

    def compose(self) -> ComposeResult:
        with Vertical(id="apply-prompt"):
            yield Label("Which resume did you use?")
            yield Input(placeholder="e.g. Software Engineering", id="resume-input")

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

    CSS_PATH = "css/DiscardPrompt.tcss"
    
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