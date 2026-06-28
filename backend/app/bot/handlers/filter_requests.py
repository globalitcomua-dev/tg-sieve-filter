from aiogram.types import Message, Update

from app.telegram.message_processor import TelegramMessageProcessor
from app.telegram.update import TelegramMessage


async def handle_filter_request(
    message: Message,
    event_update: Update,
    processor: TelegramMessageProcessor,
) -> str | None:
    text = message.text or message.caption
    if not text:
        return None

    normalized = TelegramMessage(
        update_id=event_update.update_id,
        chat_id=str(message.chat.id),
        message_id=message.message_id,
        text=text,
        username=message.from_user.username if message.from_user else None,
    )
    return processor.process(normalized)
