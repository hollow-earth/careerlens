from pydoc import describe

from textual.app import App, ComposeResult
from textual.widgets import DataTable
from rich.text import Text

from database import get_jobs_for_display, connect, close

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

class TableApp(App):  # pyright: ignore[reportMissingTypeArgument]
    def compose(self) -> ComposeResult:
        yield DataTable()

    def on_mount(self) -> None:
        conn = connect()
        table = self.query_one(DataTable)
        for header, _, width in COLUMNS:
            table.add_column(header, width=width)
        rows = get_jobs_for_display(conn)
        _ = table.add_rows([
            (
                truncate_text("" if row.title is None else row.title, 50),
                truncate_text("" if row.company is None else row.company, 30),
                truncate_text("" if row.description is None else row.description, 30),
                truncate_text("" if row.score is None else str(row.score), 10),
                truncate_text("" if row.status is None else row.status.value, 20),
            ) for row in rows])
        close(conn)