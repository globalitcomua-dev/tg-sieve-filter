from app.core.config import settings
from app.filters.storage import FileFilterStorage, build_filter_storage


def test_builds_file_storage_when_configured(tmp_path):
    original_backend = settings.filter_storage_backend
    original_path = settings.sieve_script_path
    settings.filter_storage_backend = "file"
    settings.sieve_script_path = tmp_path / "active.sieve"
    try:
        storage = build_filter_storage()
    finally:
        settings.filter_storage_backend = original_backend
        settings.sieve_script_path = original_path

    assert isinstance(storage, FileFilterStorage)
