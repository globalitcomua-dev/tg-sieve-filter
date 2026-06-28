from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# `BASE_DIR` нужен как "якорь" проекта.
# Благодаря ему можно одинаково находить `.env`, `data/` и другие файлы,
# независимо от того, откуда именно был запущен Python-процесс.
BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # Ниже мы описываем все настройки проекта в одном месте.
    # `BaseSettings` из Pydantic умеет автоматически подставлять значения
    # из переменных окружения и из `.env` файла.
    #
    # Для обучения это полезно как пример "централизации конфигурации":
    # код логики не ищет переменные окружения по всему проекту,
    # а получает уже готовый объект `settings`.
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_poll_interval: int = 5
    telegram_bot_name: str = "sieve-filter"
    telegram_drop_pending_updates_on_start: bool = True

    # Файл SQLite используется для небольшого локального состояния:
    # здесь храним последний обработанный Telegram update_id и журнал обработки.
    state_db_path: Path = BASE_DIR / "data" / "state.sqlite3"

    # Через этот флаг можно переключать "куда писать итоговый sieve-скрипт":
    # либо в Mailcow DB, либо в обычный файл.
    # Это пример стратегии/полиморфизма через конфиг.
    filter_storage_backend: str = "mailcow_db"
    sieve_script_path: Path = BASE_DIR / "data" / "active.sieve"

    # `auto_apply=False` превращает проект в режим предпросмотра:
    # правило строится, но не записывается.
    # Для реальной эксплуатации это полезно как safe mode.
    auto_apply: bool = True
    allow_duplicate_rules: bool = False

    # Настройки подключения к Mailcow MySQL/MariaDB.
    # Они используются только если выбран backend `mailcow_db`.
    mailcow_db_host: str = "127.0.0.1"
    mailcow_db_port: int = 3306
    mailcow_db_name: str = "mailcow"
    mailcow_db_user: str = "mailcow"
    mailcow_db_password: str = ""
    mailcow_filter_username: str = "info@nexus.ua"
    mailcow_filter_type: str = "postfilter"
    mailcow_filter_name: str = "postfilter"
    mailcow_filter_desc: str = "Auto-maintained postfilter"

    # IMAP-проверка папки опциональна.
    # Если включить её, перед записью правила сервис проверит,
    # существует ли указанная папка в целевом ящике.
    imap_validate_mailbox: bool = False
    imap_default_port: int = 993
    imap_use_ssl: bool = True
    imap_password: str = ""
    imap_passwords_json: dict[str, str] = Field(default_factory=dict)

    # Этот префикс попадает в комментарий над каждым созданным правилом.
    # Он помогает человеку быстро находить в script_data, где начинается правило.
    rule_comment_prefix: str = "# rule:"
    log_level: str = "INFO"

    # `extra="ignore"` означает:
    # если в `.env` есть лишние переменные, приложение не упадёт.
    # Это удобно на серверах, где один `.env` иногда используется шире,
    # чем один конкретный проект.
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Создаём один общий объект настроек на весь процесс.
# Это типичный паттерн: один раз загрузили конфиг и потом импортируем его отовсюду.
settings = Settings()
