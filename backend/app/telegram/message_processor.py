import logging

from app.core.config import settings
from app.filters.models import ApplyResult
from app.repositories.state import StateRepository
from app.services.filter_request_service import FilterRequestService
from app.telegram.filters import is_allowed_chat, is_command
from app.telegram.update import TelegramMessage


logger = logging.getLogger(__name__)


class TelegramMessageProcessor:
    # Этот класс принимает уже нормализованное текстовое сообщение
    # и применяет к нему всю текущую бизнес-логику фильтров.
    # Благодаря этому мы можем менять транспортный слой Telegram
    # (ручной polling, aiogram handlers и т.д.), не переписывая ядро обработки.
    def __init__(
        self,
        repository: StateRepository,
        request_service: FilterRequestService,
        bot_name: str,
    ):
        self.repository = repository
        self.request_service = request_service
        self.bot_name = bot_name

    def process(self, message: TelegramMessage) -> ApplyResult:
        logger.info(
            "Processing message: update_id=%s message_id=%s chat_id=%s username=%s configured_chat_id=%s text_preview=%r",
            message.update_id,
            message.message_id,
            message.chat_id,
            message.username,
            settings.telegram_chat_id or "<any>",
            message.text[:200],
        )

        if not is_allowed_chat(message):
            logger.warning(
                "Skipping message because chat_id is not allowed: actual=%s expected=%s",
                message.chat_id,
                settings.telegram_chat_id,
            )
            self.repository.save_processed_request(
                update_id=message.update_id,
                message_id=message.message_id,
                status="skipped-chat",
                details=f"chat_id={message.chat_id}",
            )
            return ApplyResult(status="skipped-chat", summary=f"chat_id={message.chat_id}")

        if is_command(message):
            logger.info("Ignoring bot command: message_id=%s text=%r", message.message_id, message.text[:200])
            self.repository.save_processed_request(
                update_id=message.update_id,
                message_id=message.message_id,
                status="ignored-command",
                details=message.text,
            )
            return ApplyResult(status="ignored-command", summary="bot command ignored")

        result = self.request_service.process_message(message.text)
        logger.info(
            "Business processing finished: message_id=%s status=%s summary=%s",
            message.message_id,
            result.status,
            result.summary,
        )
        self.repository.save_processed_request(
            update_id=message.update_id,
            message_id=message.message_id,
            status=result.status,
            details=result.summary,
        )
        return result
