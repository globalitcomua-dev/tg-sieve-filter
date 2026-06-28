from app.core.config import settings
from app.telegram.update import TelegramMessage


def is_allowed_chat(message: TelegramMessage) -> bool:
    if not settings.telegram_chat_id:
        return True
    return message.chat_id == str(settings.telegram_chat_id)


def is_command(message: TelegramMessage) -> bool:
    return message.text.strip().startswith("/")
