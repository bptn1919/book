import os
from pathlib import Path

STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")


def book_path(project_id: str) -> Path:
    return Path(STORAGE_DIR) / project_id / "book.txt"


def save_book(project_id: str, content: bytes) -> None:
    path = book_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
