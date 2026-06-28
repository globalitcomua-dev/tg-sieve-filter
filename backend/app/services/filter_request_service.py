import logging

from app.core.config import settings
from app.filters.mailbox import MailboxValidator
from app.filters.models import ApplyResult
from app.filters.parser import FilterRequestParser
from app.filters.storage import build_filter_storage
from app.filters.writer import SieveScriptWriter


logger = logging.getLogger(__name__)


class FilterRequestService:
    def __init__(self):
        # Этот сервис собирает три шага в один понятный pipeline:
        # 1. распознать заявку,
        # 2. проверить доступность папки,
        # 3. записать/подготовить правило.
        self.parser = FilterRequestParser()
        self.mailbox_validator = MailboxValidator()
        self.writer = SieveScriptWriter(build_filter_storage())

    def process_message(self, text: str) -> ApplyResult:
        # Parser пытается извлечь структуру из обычного человеческого текста.
        # Если структура не найдена, значит сообщение не похоже на заявку.
        logger.info("FilterRequestService received text_preview=%r", text[:200])
        request = self.parser.parse(text)
        if not request:
            logger.info("Message ignored: parser did not detect a filter request")
            return ApplyResult(status="ignored", summary="message does not look like a filter request")

        logger.info(
            "Parsed filter request: match_type=%s values=%s mailbox_user=%s mailbox_host=%s folder_path=%s",
            request.match_type,
            request.values,
            request.target.mailbox_user,
            request.target.mailbox_host,
            request.target.folder_path,
        )

        # Это дополнительная "защита реальностью":
        # даже если текст красивый, папка может не существовать.
        mailbox_ok, mailbox_summary = self.mailbox_validator.validate(request.target)
        if not mailbox_ok:
            logger.warning("Mailbox validation failed: %s", mailbox_summary)
            return ApplyResult(status="invalid-mailbox", summary=mailbox_summary)

        # Если и парсинг, и валидация прошли успешно — применяем правило.
        logger.info("Mailbox validation passed: %s", mailbox_summary)
        return self.writer.apply(request)
