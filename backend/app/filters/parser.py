import re
from urllib.parse import unquote, urlparse

from app.filters.detector import is_filter_request_candidate
from app.filters.models import FilterRequest, MailboxTarget


# Регулярные выражения — это инструмент поиска шаблонов в строках.
# Здесь они нужны, чтобы извлекать email-адреса, домены и языковые маркеры
# вроде "все, що завершується на @domain.com".
EMAIL_RE = re.compile(r"(?i)\b[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}\b")
DOMAIN_RE = re.compile(r"(?i)(?<![a-z0-9._%+\-])@([a-z0-9.\-]+\.[a-z]{2,})")
DOMAIN_WIDE_RE = re.compile(
    r"(?i)(?:any\s+address|all\s+addresses|любые\s+адреса|все,\s*що\s*завершується|"
    r"все,\s*что\s*заканчивается|усі,\s*що\s*завершуються|все\s+что\s+заканчивается|"
    r"anything\s+ending\s+with)"
)


class FilterRequestParser:
    def parse(self, text: str) -> FilterRequest | None:
        # Сначала запускаем detector.
        # Это отдельный быстрый слой, который отсеивает явный шум
        # до более дорогого и детального парсинга.
        if not is_filter_request_candidate(text):
            return None

        # Ищем место, где начинается IMAP URI.
        # Всё до него — это обычно "человеческая часть" заявки,
        # а всё после него — техническое описание целевой папки.
        marker_index = text.lower().find("imap://")
        imap_uri = self._extract_imap_uri(text)
        if not imap_uri:
            return None

        target = self._parse_imap_target(imap_uri)
        request_text = text[:marker_index] if marker_index >= 0 else text

        # `dict.fromkeys(...)` используется как простой способ убрать дубли,
        # сохранив исходный порядок найденных адресов.
        emails = list(
            dict.fromkeys(match.group(0).lower() for match in EMAIL_RE.finditer(request_text))
        )
        domain_mentions = list(
            dict.fromkeys(match.group(1).lower() for match in DOMAIN_RE.finditer(request_text))
        )

        # Здесь пытаемся понять, хочет ли пользователь фильтр на весь домен,
        # а не только на конкретный email.
        #
        # `explicit_domain_wide` — в тексте есть явные фразы вроде
        # "любые адреса с @domain.com".
        explicit_domain_wide = bool(DOMAIN_WIDE_RE.search(request_text))

        # `bare_domain_wide` — иногда пользователь просто пишет `@domain.com`
        # без длинной поясняющей фразы, и это тоже надо распознать как домен.
        bare_domain_wide = any(
            f"@{domain}" in request_text
            and domain not in {email.split("@", 1)[1] for email in emails}
            for domain in domain_mentions
        )
        is_domain_wide = explicit_domain_wide or bare_domain_wide

        if is_domain_wide and domain_mentions:
            # Для доменного фильтра в values оставляем только одно значение `@domain`.
            values = [f"@{domain_mentions[-1]}"]
            return FilterRequest(
                original_text=text,
                target=target,
                match_type="domain",
                values=values,
            )

        if emails:
            # Если доменный сценарий не сработал, строим фильтр по списку email-адресов.
            return FilterRequest(
                original_text=text,
                target=target,
                match_type="address",
                values=emails,
            )

        return None

    @staticmethod
    def _extract_imap_uri(text: str) -> str | None:
        # Здесь мы не используем сложный URL parser сразу,
        # а сначала грубо выделяем "хвост" строки, начиная с `imap://`.
        marker_index = text.lower().find("imap://")
        if marker_index < 0:
            return None

        candidate = text[marker_index:].strip()
        candidate = candidate.splitlines()[0].strip()

        # Убираем типичные "хвосты" вроде точки или закрывающей скобки,
        # которые часто прилипают к ссылке в живой переписке.
        return candidate.rstrip(".,);")

    def _parse_imap_target(self, imap_uri: str) -> MailboxTarget:
        # `urlparse` разбирает URI на части: username, host, path и т.д.
        parsed = urlparse(imap_uri)
        mailbox_user = unquote(parsed.username or "")
        mailbox_host = parsed.hostname or ""
        folder_path = self._normalize_folder_path(unquote(parsed.path or ""))
        if not folder_path:
            raise ValueError(f"IMAP URI does not contain a folder path: {imap_uri}")

        # Возвращаем не словарь, а dataclass-структуру.
        # Это делает код ниже более читаемым и типизированным.
        return MailboxTarget(
            imap_uri=imap_uri,
            mailbox_user=mailbox_user,
            mailbox_host=mailbox_host,
            folder_path=folder_path,
        )

    @staticmethod
    def _normalize_folder_path(raw_path: str) -> str:
        # Здесь обычный цикл "очищает" путь от лишних пробелов и пустых сегментов.
        # Пример:
        # `"/OFFSHORE/+Clients/ Kentaro"` -> `"OFFSHORE/+Clients/Kentaro"`.
        segments = [segment.strip() for segment in raw_path.split("/") if segment.strip()]
        return "/".join(segments)
