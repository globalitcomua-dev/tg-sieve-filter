from pydantic import BaseModel


class TelegramMessage(BaseModel):
    update_id: int
    chat_id: str
    message_id: int | None = None
    text: str
    username: str | None = None


def parse_update(update: dict) -> TelegramMessage | None:
    message = update.get("message") or update.get("channel_post")
    if not message:
        return None

    text = message.get("text") or message.get("caption")
    if not text:
        return None

    chat = message.get("chat") or {}
    user = message.get("from") or {}

    return TelegramMessage(
        update_id=update["update_id"],
        chat_id=str(chat.get("id", "")),
        message_id=message.get("message_id"),
        text=text,
        username=user.get("username"),
    )
