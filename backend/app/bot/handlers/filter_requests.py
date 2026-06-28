from aiogram.types import Message, Update

from app.bot.reply_formatter import GroupReplyFormatter
from app.telegram.message_processor import TelegramMessageProcessor
from app.telegram.update import TelegramMessage


reply_formatter = GroupReplyFormatter()


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
    result = processor.process(normalized)
    reply_text = reply_formatter.build_reply(text=text, result=result)
    if reply_text:
        await message.reply(reply_text)
    return result.status
