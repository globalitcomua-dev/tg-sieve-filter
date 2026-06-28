import re


# В этом модуле нет полного парсинга.
# Его задача легче и быстрее: понять, стоит ли вообще пытаться разбирать текст
# как заявку на фильтр.
#
# Такой предварительный этап полезен по двум причинам:
# 1. он отсеивает шум раньше, чем включится более сложный parser;
# 2. он уменьшает ложные срабатывания на DONE/Created/цитаты старых сообщений.
IMAP_HINT_RE = re.compile(r"imap://", re.IGNORECASE)
EMAIL_OR_DOMAIN_START_RE = re.compile(
    r"^\s*(?:new\b|[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}|@[a-z0-9.\-]+\.[a-z]{2,})",
    re.IGNORECASE,
)
STATUS_PREFIX_RE = re.compile(
    r"^\s*(?:done\b|created\b|create\b|added\b|add\b|зробив\b|зробев\b|це можна\b|"
    r"временно\b|проверьте\b|перевірте\b|check\b|✅\s*done\b)",
    re.IGNORECASE,
)
DISCUSSION_HINT_RE = re.compile(
    r"(?:работник, который хочет создать фильтр|пример создания нового фильтра|"
    r"пишет в этот чат|когда максим добавит фильтр|below, example|ниже, пример)",
    re.IGNORECASE,
)
QUOTED_CHAT_RE = re.compile(r"\bFexus [^,\n]+,\s*\[\d{2}\.\d{2}\.\d{2}\s+\d{1,2}:\d{2}\]")


def is_filter_request_candidate(text: str) -> bool:
    # Самая дешёвая и быстрая проверка:
    # если нет `imap://`, это почти наверняка не заявка на почтовый фильтр.
    if not IMAP_HINT_RE.search(text):
        return False

    normalized = text.strip()
    if not normalized:
        return False

    # Статусные ответы команды часто содержат цитату исходной заявки.
    # Без этой проверки parser попытался бы воспринять их как новые запросы.
    if STATUS_PREFIX_RE.search(normalized):
        return False

    # Отсекаем "мета"-сообщения с объяснением процесса, примерами и инструкциями.
    if DISCUSSION_HINT_RE.search(normalized):
        return False

    # Отсекаем длинные цитаты Telegram-истории внутри сообщений.
    if QUOTED_CHAT_RE.search(normalized):
        return False

    lowered = normalized.lower()
    if "done" in lowered and "new" in lowered and not EMAIL_OR_DOMAIN_START_RE.search(normalized):
        return False

    # Финальная эвристика:
    # либо текст сразу начинается как заявка,
    # либо в нём хотя бы есть " new " как маркер живой формулировки.
    return EMAIL_OR_DOMAIN_START_RE.search(normalized) is not None or " new " in f" {lowered} "
