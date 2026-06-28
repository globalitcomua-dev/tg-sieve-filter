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
            if result.summary.startswith("mailbox not found") and folder:
                return f"Не обнаружил папку, либо она названа иначе: {folder}"
            if result.summary.startswith("IMAP connection failed"):
                return f"Не смог подключиться к IMAP для проверки папки: {result.summary}"
            if result.summary.startswith("IMAP login failed"):
                return "Не смог войти в IMAP для проверки папки. Проверь логин/пароль ящика."
            if result.summary.startswith("IMAP LIST failed"):
                return f"IMAP ответил ошибкой при проверке папки: {result.summary}"
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
