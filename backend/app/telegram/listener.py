from app.core.config import settings
from app.repositories.state import StateRepository
from app.services.filter_request_service import FilterRequestService
from app.telegram.client import TelegramClient
from app.telegram.message_processor import TelegramMessageProcessor
from app.telegram.service import TelegramService


def run_listener() -> None:
    # Проверяем конфиг сразу при старте, чтобы упасть с понятной ошибкой,
    # а не получить менее очевидный сбой позже внутри HTTP-запроса к Telegram.
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    # Здесь собираются главные зависимости приложения.
    # Это похоже на простой ручной dependency injection:
    # отдельно создаём хранилище состояния, бизнес-логику и HTTP-клиент,
    # а потом передаём всё это в orchestrator-класс `TelegramService`.
    repository = StateRepository(settings.state_db_path)
    request_service = FilterRequestService()
    message_processor = TelegramMessageProcessor(
        repository=repository,
        request_service=request_service,
        bot_name=settings.telegram_bot_name,
    )
    client = TelegramClient(settings.telegram_bot_token)
    service = TelegramService(
        client=client,
        repository=repository,
        message_processor=message_processor,
        bot_name=settings.telegram_bot_name,
    )

    # После инициализации управление передаётся в бесконечный цикл polling.
    service.run_forever()
