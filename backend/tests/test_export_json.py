import os
from pathlib import Path

from app.filters.parser import FilterRequestParser
from app.telegram.export_json import load_telegram_desktop_export


def _get_export_path() -> Path | None:
    raw_path = os.getenv("TELEGRAM_EXPORT_JSON_PATH", "").strip()
    if not raw_path:
        return None

    export_path = Path(raw_path)
    if not export_path.exists():
        return None

    return export_path


def test_loads_selected_real_export_messages():
    export_path = _get_export_path()
    if export_path is None:
        return

    messages = load_telegram_desktop_export(export_path)

    assert len(messages) > 400
    assert any("@wise.com" in message.text for message in messages)


def test_real_export_contains_recognizable_requests():
    export_path = _get_export_path()
    if export_path is None:
        return

    parser = FilterRequestParser()
    requests = [
        request
        for request in (parser.parse(message.text) for message in load_telegram_desktop_export(export_path))
        if request is not None
    ]

    assert len(requests) >= 120
    assert any(request.values == ["@wise.com"] for request in requests)
    assert any(
        request.target.folder_path == "OFFSHORE/+CSPs/UNITED_KINGDOM/Companies_House_UK"
        for request in requests
    )
