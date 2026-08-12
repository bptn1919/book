import pytest

from app import models, storage


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(storage, "STORAGE_DIR", str(tmp_path / "storage"))
