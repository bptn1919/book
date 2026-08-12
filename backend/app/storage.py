import base64
import os
from pathlib import Path

STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")


def book_path(project_id: str) -> Path:
    return Path(STORAGE_DIR) / project_id / "book.txt"


def save_book(project_id: str, content: bytes) -> None:
    path = book_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def save_image(project_id: str, filename: str, data_b64: str) -> None:
    path = Path(STORAGE_DIR) / project_id / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(data_b64))


def image_path(project_id: str, filename: str) -> Path:
    return Path(STORAGE_DIR) / project_id / filename
