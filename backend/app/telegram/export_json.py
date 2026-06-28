import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ExportMessage:
    # Эта структура нужна для локального анализа Telegram Desktop export.
    # Она проще исходного JSON и содержит только то, что полезно парсеру.
    id: int
    date: str
    author: str | None
    text: str


def load_telegram_desktop_export(path: str | Path) -> list[ExportMessage]:
    # Отдельный loader удобен для регрессионных тестов:
    # можно взять живую выгрузку из Telegram Desktop и массово прогнать её
    # через detector/parser, не подключаясь к Telegram API.
    export_path = Path(path)
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    messages: list[ExportMessage] = []

    # Перебираем все элементы массива `messages`,
    # но оставляем только обычные текстовые сообщения.
    for item in payload.get("messages", []):
        if item.get("type") != "message":
            continue
        messages.append(
            ExportMessage(
                id=item["id"],
                date=item.get("date", ""),
                author=item.get("from"),
                text=_flatten_text(item.get("text", "")),
            )
        )

    return messages


def _flatten_text(value) -> str:
    # В Telegram Desktop export поле `text` может быть:
    # 1. обычной строкой,
    # 2. списком кусочков текста и entity-объектов.
    #
    # Эта функция нормализует оба варианта в одну строку,
    # чтобы parser ниже работал с единым форматом.
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text", "")))
        return "".join(parts)
    return str(value)
