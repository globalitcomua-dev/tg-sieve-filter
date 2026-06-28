from app.repositories.state import StateRepository
from app.services.filter_request_service import FilterRequestService
from app.telegram.filters import is_allowed_chat, is_command
from app.telegram.update import TelegramMessage


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

    def process(self, message: TelegramMessage) -> str:
        if not is_allowed_chat(message):
            print(f"Skip chat_id={message.chat_id}", flush=True)
            self.repository.save_processed_request(
                update_id=message.update_id,
                message_id=message.message_id,
                status="skipped-chat",
                details=f"chat_id={message.chat_id}",
            )
            return "skipped-chat"

        if is_command(message):
            self.repository.save_processed_request(
                update_id=message.update_id,
                message_id=message.message_id,
                status="ignored-command",
                details=message.text,
            )
            return "ignored-command"

        result = self.request_service.process_message(message.text)
        self.repository.save_processed_request(
            update_id=message.update_id,
            message_id=message.message_id,
            status=result.status,
            details=result.summary,
        )
        print(
            f"Processed telegram message_id={message.message_id} status={result.status}: {result.summary}",
            flush=True,
        )
        return result.status
