from textual.app import App, ComposeResult
from textual.widgets import DataTable
from rich.text import Text

from database import get_jobs_for_display, connect, close

COLUMN_HEADERS = (
        "Title", 
        "Company", 
        "Location", 
        "Score", 
        "Status", 
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
        table.add_column(COLUMN_HEADERS[0], width=50)
        table.add_column(COLUMN_HEADERS[1], width=30)
        table.add_column(COLUMN_HEADERS[2], width=30)
        table.add_column(COLUMN_HEADERS[3], width=10)
        table.add_column(COLUMN_HEADERS[4], width=20)
        rows = get_jobs_for_display(conn)
        _ = table.add_rows([
            (
                truncate_text(row["title"], 50),
                truncate_text(row["company"], 30),
                truncate_text(row["location"], 30),
                truncate_text(str(row["score"]), 10),
                truncate_text(row["status"], 20),
            ) for row in rows])
        close(conn)