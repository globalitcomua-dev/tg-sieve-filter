from app.filters.models import ApplyResult
from app.filters.parser import FilterRequestParser


class GroupReplyFormatter:
    def __init__(self) -> None:
        self.parser = FilterRequestParser()

    def build_reply(self, text: str, result: ApplyResult) -> str | None:
        request = self.parser.parse(text)
        folder = request.target.folder_path if request else None
        values = ", ".join(request.values) if request else None

        if result.status == "applied":
            if values and folder:
                return f"✅DONE - {values} - {folder}"
            return "✅DONE"

        if result.status == "invalid-mailbox":
            if folder:
                return f"Не обнаружил папку, либо она названа иначе: {folder}"
            return "Не обнаружил папку, либо она названа иначе."

        if result.status == "duplicate":
            return f"Найден дубль: {result.summary}"

        if result.status == "conflict":
            return f"Конфликт правила: {result.summary}"

        if result.status == "dry-run":
            if values and folder:
                return f"DRY-RUN - {values} - {folder}"
            return f"DRY-RUN - {result.summary}"

        return None
