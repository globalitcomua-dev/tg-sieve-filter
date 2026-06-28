import asyncio

from aiogram import Bot, Dispatcher
from aiogram.methods import DeleteWebhook

from app.bot.routers import build_routers
from app.core.config import settings
from app.repositories.state import StateRepository
from app.services.filter_request_service import FilterRequestService
from app.telegram.message_processor import TelegramMessageProcessor


async def _run_bot() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    repository = StateRepository(settings.state_db_path)
    request_service = FilterRequestService()
    processor = TelegramMessageProcessor(
        repository=repository,
        request_service=request_service,
        bot_name=settings.telegram_bot_name,
    )

    bot = Bot(settings.telegram_bot_token)
    dispatcher = Dispatcher()
    for router in build_routers(processor):
        dispatcher.include_router(router)

    # Если флаг включён, на старте сбрасываем накопившиеся pending updates.
    # Это удобно, когда бот впервые приходит в уже давно живущий рабочий чат.
    await bot(DeleteWebhook(drop_pending_updates=settings.telegram_drop_pending_updates_on_start))

    await dispatcher.start_polling(
        bot,
        allowed_updates=dispatcher.resolve_used_update_types(),
    )


def run_bot() -> None:
    asyncio.run(_run_bot())
