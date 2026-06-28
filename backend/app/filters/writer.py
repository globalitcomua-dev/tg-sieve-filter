from app.core.config import settings
from app.filters.models import ApplyResult, FilterRequest
from app.filters.renderer import SieveRuleRenderer
from app.filters.storage import FilterStorage


class SieveScriptWriter:
    def __init__(self, storage: FilterStorage):
        # Writer отвечает именно за "правила записи":
        # как собрать финальный script, когда считать заявку дублем,
        # когда запрещать конфликт и когда реально сохранять результат.
        self.storage = storage
        self.renderer = SieveRuleRenderer()

    def apply(self, request: FilterRequest) -> ApplyResult:
        # Сначала читаем текущее содержимое script_data/файла,
        # чтобы не писать "вслепую".
        existing = self.storage.load_script()
        rendered = self.renderer.render(request)

        # Проверка дубля нужна для идемпотентности:
        # повторный запуск на том же сообщении не должен плодить копии правил.
        duplicate_reason = self._detect_duplicate(existing, request)
        if duplicate_reason and not settings.allow_duplicate_rules:
            return ApplyResult(
                status="duplicate",
                summary=duplicate_reason,
                rendered_rule=rendered,
            )

        if request.match_type == "domain":
            # Доменные правила более "широкие", чем одиночные email.
            # Поэтому отдельно ловим конфликт:
            # домен уже есть, но ведёт в другую папку.
            conflict_reason = self._detect_domain_conflict(existing, request)
            if conflict_reason:
                return ApplyResult(
                    status="conflict",
                    summary=conflict_reason,
                    rendered_rule=rendered,
            )

        if not settings.auto_apply:
            # dry-run полезен для обучения, тестирования и безопасного просмотра результата.
            return ApplyResult(
                status="dry-run",
                summary=f"rule prepared for {request.target.folder_path}",
                rendered_rule=rendered,
            )

        # Этот блок аккуратно склеивает старый и новый текст.
        # Он следит за переносами строк, чтобы итоговый sieve script
        # оставался читаемым и не слипался в одну строку.
        needs_separator = bool(existing and not existing.endswith("\n"))
        new_content = existing
        if needs_separator:
            new_content += "\n"
        if existing and not existing.endswith("\n\n"):
            new_content += "\n"
        new_content += rendered
        destination = self.storage.save_script(new_content)
        return ApplyResult(
            status="applied",
            summary=f"rule appended to {destination}",
            rendered_rule=rendered,
        )

    def _detect_duplicate(self, existing: str, request: FilterRequest) -> str | None:
        # Сначала проверяем, что правило указывает на ту же папку,
        # а затем убеждаемся, что все значения (email/домен) уже встречаются в script.
        folder_marker = f'fileinto "{request.target.folder_path}";'
        if folder_marker in existing:
            if all(value in existing for value in request.values):
                return f"matching rule already exists for {request.target.folder_path}"
        return None

    def _detect_domain_conflict(self, existing: str, request: FilterRequest) -> str | None:
        # Если домен уже есть в другом правиле, не стоит молча добавлять второе.
        # Лучше остановиться и пометить заявку как конфликтную.
        domain_value = request.values[0]
        folder_marker = f'fileinto "{request.target.folder_path}";'
        if domain_value in existing and folder_marker not in existing:
            return f"domain {domain_value} already exists in another rule"
        return None
