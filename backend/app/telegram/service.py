import time

from app.core.config import settings
from app.repositories.state import StateRepository
from app.telegram.message_processor import TelegramMessageProcessor
from app.telegram.update import parse_update


class TelegramService:
    # Этот класс координирует жизненный цикл listener'а:
    # 1. получает обновления из Telegram,
    # 2. превращает raw update в удобную структуру,
    # 3. фильтрует неподходящие сообщения,
    # 4. запускает бизнес-обработку,
    # 5. сохраняет offset, чтобы не обрабатывать те же сообщения повторно.
    def __init__(
        self,
        client,
        repository: StateRepository,
        message_processor: TelegramMessageProcessor,
        bot_name: str,
    ):
        self.client = client
        self.repository = repository
        self.message_processor = message_processor
        self.bot_name = bot_name

    def poll_once(self) -> None:
        # Offset в Telegram нужен для "продолжения с места остановки".
        # Мы читаем последний update_id из SQLite и просим Telegram вернуть
        # только новые сообщения, а не всю историю заново.
        last_update_id = self.repository.get_last_update_id(self.bot_name)
        offset = last_update_id + 1 if last_update_id is not None else None
        updates = self.client.get_updates(offset=offset, timeout=30)

        # Цикл `for` здесь перебирает все обновления, которые пришли за один poll.
        # Циклы нужны, когда одну и ту же операцию надо повторить для набора элементов.
        # В данном случае одна и та же операция — это `process_update(update)`.
        for update in updates:
            self.process_update(update)

    def process_update(self, update: dict) -> None:
        # Telegram update — это сырой словарь от API.
        # Сначала достаём технический id обновления, который нужен для offset.
        update_id = update["update_id"]

        # Затем пытаемся превратить update в более удобный объект сообщения.
        # Если внутри вообще нет текстового сообщения, parser вернёт `None`.
        message = parse_update(update)

        if not message:
            # Даже "неинтересный" update нужно отметить как обработанный,
            # иначе listener будет получать его снова и снова.
            self.repository.save_last_update_id(self.bot_name, update_id)
            return

        # Здесь transport layer только извлекает update,
        # а сама логика работы с сообщением вынесена в отдельный processor.
        # Это создаёт мост к будущей aiogram router/handler архитектуре.
        self.message_processor.process(message)

        # Offset сохраняем только после обработки текущего update,
        # чтобы при падении между poll'ами не "перепрыгнуть" необработанные данные.
        self.repository.save_last_update_id(self.bot_name, update_id)

    def run_forever(self) -> None:
        print("Telegram sieve filter listener started", flush=True)

        # Бесконечный цикл — стандартный паттерн для long-running listener/service.
        # Он постоянно опрашивает Telegram и ждёт новые события.
        while True:
            try:
                self.poll_once()
            except Exception as exc:
                # Небольшая задержка защищает от "горячего" бесконечного спама ошибками.
                # Например, если временно недоступна сеть или Telegram API.
                print(f"Telegram service error: {exc}", flush=True)
                time.sleep(settings.telegram_poll_interval)
