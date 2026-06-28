from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, Update

from app.bot.handlers.filter_requests import handle_filter_request
from app.telegram.message_processor import TelegramMessageProcessor


def build_group_router(processor: TelegramMessageProcessor) -> Router:
    router = Router(name="group-filter-requests")

    @router.message(F.chat.type.in_({"group", "supergroup"}), F.text | F.caption)
    async def on_group_message(message: Message, event_update: Update) -> None:
        await handle_filter_request(message=message, event_update=event_update, processor=processor)

    return router


def build_private_router() -> Router:
    router = Router(name="private-future-commands")

    @router.message(F.chat.type == "private", CommandStart())
    async def on_private_start(message: Message) -> None:
        await message.answer(
            "Бот активен. Сейчас основной сценарий — обработка заявок на фильтры в группе. "
            "Личные команды и справочная логика будут добавляться поверх aiogram routers."
        )

    @router.message(F.chat.type == "private")
    async def on_private_message(message: Message) -> None:
        await message.answer(
            "Личный режим пока в подготовке. Архитектура уже готова для будущих "
            "команд по Mailcow и документации Fexus."
        )

    return router


def build_routers(processor: TelegramMessageProcessor) -> list[Router]:
    return [
        build_group_router(processor),
        build_private_router(),
    ]
