import requests


class TelegramClient:
    def __init__(self, bot_token: str):
        # Telegram Bot API работает через обычные HTTP-запросы.
        # Поэтому достаточно собрать base URL с токеном и дальше вызывать endpoints.
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict]:
        # `allowed_updates` ограничивает типы событий,
        # которые нам вообще интересны.
        params: dict[str, object] = {
            "timeout": timeout,
            "allowed_updates": ["message", "channel_post"],
        }
        if offset is not None:
            params["offset"] = offset

        # Long polling:
        # Telegram может подождать до `timeout` секунд, прежде чем ответить,
        # если новых сообщений пока нет.
        response = requests.get(
            f"{self.base_url}/getUpdates",
            params=params,
            timeout=timeout + 10,
        )
        response.raise_for_status()
        payload = response.json()

        # Сначала проверяем HTTP-успех (`raise_for_status`),
        # а затем прикладной успех самого Telegram API (`ok`).
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram API error: {payload}")
        return payload.get("result", [])
