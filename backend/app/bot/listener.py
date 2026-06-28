import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.methods import DeleteWebhook

from app.bot.routers import build_routers
from app.core.config import settings
from app.core.logging import configure_logging
from app.repositories.state import StateRepository
from app.services.filter_request_service import FilterRequestService
from app.telegram.message_processor import TelegramMessageProcessor


logger = logging.getLogger(__name__)


async def _run_bot() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    logger.info(
        "Starting bot: bot_name=%s chat_id=%s backend=%s auto_apply=%s drop_pending=%s state_db=%s",
        settings.telegram_bot_name,
        settings.telegram_chat_id or "<any>",
        settings.filter_storage_backend,
        settings.auto_apply,
        settings.telegram_drop_pending_updates_on_start,
        settings.state_db_path,
    )

    repository = StateRepository(settings.state_db_path)
    request_service = FilterRequestService()
    processor = TelegramMessageProcessor(
        repository=repository,
        request_service=request_service,
        bot_name=settings.telegram_bot_name,
    )

    bot = Bot(settings.telegram_bot_token)
    me = await bot.get_me()
    logger.info(
        "Telegram getMe ok: id=%s username=@%s can_join_groups=%s can_read_all_group_messages=%s",
        me.id,
        me.username,
        me.can_join_groups,
        me.can_read_all_group_messages,
    )
    webhook = await bot.get_webhook_info()
    logger.info(
        "Telegram webhook status: url=%s pending_update_count=%s last_error_date=%s last_error_message=%s",
        webhook.url or "<none>",
        webhook.pending_update_count,
        webhook.last_error_date,
        webhook.last_error_message,
    )

    dispatcher = Dispatcher()
    for router in build_routers(processor):
        dispatcher.include_router(router)
        logger.info("Router attached: %s", router.name)

    # Если флаг включён, на старте сбрасываем накопившиеся pending updates.
    # Это удобно, когда бот впервые приходит в уже давно живущий рабочий чат.
    logger.info(
        "Calling DeleteWebhook(drop_pending_updates=%s)",
        settings.telegram_drop_pending_updates_on_start,
    )
    await bot(DeleteWebhook(drop_pending_updates=settings.telegram_drop_pending_updates_on_start))

    allowed_updates = dispatcher.resolve_used_update_types()
    logger.info("Starting polling with allowed_updates=%s", allowed_updates)
    await dispatcher.start_polling(
        bot,
        allowed_updates=allowed_updates,
    )


def run_bot() -> None:
    configure_logging()
    asyncio.run(_run_bot())
