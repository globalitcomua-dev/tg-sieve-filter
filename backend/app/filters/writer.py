import re
from dataclasses import dataclass

from app.core.config import settings
from app.filters.models import ApplyResult, FilterRequest
from app.filters.renderer import SieveRuleRenderer
from app.filters.storage import FilterStorage


@dataclass(slots=True)
class ParsedRuleBlock:
    start: int
    end: int
    folder_path: str
    values: list[str]
    text: str


@dataclass(slots=True)
class RuleExtension:
    start: int
    end: int
    original_rule: str
    updated_rule: str


@dataclass(slots=True)
class RuleMatch:
    reason: str
    block: ParsedRuleBlock


class SieveScriptWriter:
    RULE_BLOCK_RE = re.compile(
        r'(?ms)(?P<rule>'
        r'(?P<comment>^[^\n]*\n)?'
        r'if address :contains \["From","To","Cc"\] \[(?P<values>[^\]]*)\]\n'
        r'\{\n'
        r'  fileinto "(?P<folder>[^"]+)";\n'
        r'  stop;\n'
        r'\}\n?'
        r')'
    )

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
        extension = self._build_extension(existing, request)

        # Проверка дубля нужна для идемпотентности:
        # повторный запуск на том же сообщении не должен плодить копии правил.
        duplicate_match = self._detect_duplicate(existing, request)
        if duplicate_match and not settings.allow_duplicate_rules:
            return ApplyResult(
                status="duplicate",
                summary=duplicate_match.reason,
                rendered_rule=rendered,
                related_rule=duplicate_match.block.text,
            )

        # Доменные значения требуют более осторожной обработки:
        # один и тот же домен в другой папке даёт неоднозначную маршрутизацию.
        conflict_match = self._detect_domain_conflict(existing, request)
        if conflict_match:
            return ApplyResult(
                status="conflict",
                summary=conflict_match.reason,
                rendered_rule=rendered,
                related_rule=conflict_match.block.text,
            )

        if not settings.auto_apply:
            # dry-run полезен для обучения, тестирования и безопасного просмотра результата.
            return ApplyResult(
                status="dry-run",
                summary=(
                    f"rule prepared by extending {request.target.folder_path}"
                    if extension
                    else f"rule prepared for {request.target.folder_path}"
                ),
                rendered_rule=extension.updated_rule if extension else rendered,
                related_rule=extension.original_rule if extension else None,
            )

        if extension:
            new_content = existing[: extension.start] + extension.updated_rule + existing[extension.end :]
        else:
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
            summary=(
                f"rule extended in {destination}"
                if extension
                else f"rule appended to {destination}"
            ),
            rendered_rule=extension.updated_rule if extension else rendered,
            related_rule=extension.original_rule if extension else None,
        )

    def _detect_duplicate(self, existing: str, request: FilterRequest) -> RuleMatch | None:
        # Сначала ищем правила, которые уже пишут в ту же папку,
        # а затем проверяем, покрывают ли они новые значения полностью.
        for block in self._iter_rule_blocks(existing):
            if block.folder_path != request.target.folder_path:
                continue
            if all(self._value_is_covered(value, block.values) for value in request.values):
                return RuleMatch(
                    reason=f"matching rule already exists for {request.target.folder_path}",
                    block=block,
                )
        return None

    def _detect_domain_conflict(self, existing: str, request: FilterRequest) -> RuleMatch | None:
        # Если домен уже есть в другом правиле, не стоит молча добавлять второе:
        # одно и то же письмо сможет подпасть под несколько направлений.
        request_domains = self._request_domains(request)
        for block in self._iter_rule_blocks(existing):
            block_domains = self._block_domains(block.values)
            overlap = sorted(request_domains & block_domains)
            if not overlap:
                continue
            if block.folder_path != request.target.folder_path:
                joined = ", ".join(f"@{domain}" for domain in overlap)
                return RuleMatch(
                    reason=f"domain {joined} already routes to {block.folder_path}",
                    block=block,
                )
            if request.match_type == "domain" and any(
                not value.startswith("@") and value.split("@", 1)[1] in overlap
                for value in block.values
            ):
                joined = ", ".join(f"@{domain}" for domain in overlap)
                return RuleMatch(
                    reason=f"domain-wide rule {joined} would broaden an existing address rule in {block.folder_path}",
                    block=block,
                )
        return None

    def _build_extension(self, existing: str, request: FilterRequest) -> RuleExtension | None:
        if request.match_type != "address":
            return None

        request_domains = self._request_domains(request)
        for block in self._iter_rule_blocks(existing):
            if block.folder_path != request.target.folder_path:
                continue
            block_domains = self._block_domains(block.values)
            if not (request_domains & block_domains):
                continue

            missing_values = [value for value in request.values if value not in block.values]
            if not missing_values:
                return None

            updated_request = FilterRequest(
                original_text=request.original_text,
                target=request.target,
                match_type="address",
                values=block.values + missing_values,
                source_hint=request.source_hint,
            )
            return RuleExtension(
                start=block.start,
                end=block.end,
                original_rule=block.text,
                updated_rule=self.renderer.render(updated_request),
            )

        return None

    def _iter_rule_blocks(self, existing: str) -> list[ParsedRuleBlock]:
        blocks: list[ParsedRuleBlock] = []
        for match in self.RULE_BLOCK_RE.finditer(existing):
            values = re.findall(r'"([^"]+)"', match.group("values"))
            blocks.append(
                ParsedRuleBlock(
                    start=match.start("rule"),
                    end=match.end("rule"),
                    folder_path=match.group("folder"),
                    values=values,
                    text=match.group("rule"),
                )
            )
        return blocks

    @staticmethod
    def _block_domains(values: list[str]) -> set[str]:
        domains: set[str] = set()
        for value in values:
            if value.startswith("@"):
                domains.add(value[1:].lower())
            elif "@" in value:
                domains.add(value.split("@", 1)[1].lower())
        return domains

    @staticmethod
    def _request_domains(request: FilterRequest) -> set[str]:
        return SieveScriptWriter._block_domains(request.values)

    @staticmethod
    def _value_is_covered(value: str, existing_values: list[str]) -> bool:
        if value in existing_values:
            return True
        if "@" not in value or value.startswith("@"):
            return False
        domain_value = f'@{value.split("@", 1)[1].lower()}'
        return domain_value in {item.lower() for item in existing_values}
