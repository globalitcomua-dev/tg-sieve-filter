import sqlite3
from pathlib import Path


class StateRepository:
    def __init__(self, db_path: Path):
        # Репозиторий инкапсулирует работу с SQLite.
        # Остальной код не должен знать, как именно устроены SQL-запросы.
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        # Создаём таблицы "по требованию".
        # Это упрощает первый запуск: не нужно отдельно прогонять миграции
        # для совсем небольшого локального state storage.
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists telegram_offsets (
                    bot_name text primary key,
                    last_update_id integer
                )
                """
            )
            conn.execute(
                """
                create table if not exists processed_requests (
                    update_id integer primary key,
                    message_id integer,
                    status text not null,
                    details text,
                    created_at text default current_timestamp
                )
                """
            )

    def get_last_update_id(self, bot_name: str) -> int | None:
        # Этот метод нужен offset-механизму Telegram listener'а.
        with self._connect() as conn:
            row = conn.execute(
                "select last_update_id from telegram_offsets where bot_name = ?",
                (bot_name,),
            ).fetchone()
        return None if row is None else row[0]

    def save_last_update_id(self, bot_name: str, update_id: int) -> None:
        # `on conflict ... do update` — это UPSERT:
        # либо вставить новую запись, либо обновить существующую.
        with self._connect() as conn:
            conn.execute(
                """
                insert into telegram_offsets(bot_name, last_update_id)
                values(?, ?)
                on conflict(bot_name) do update set last_update_id = excluded.last_update_id
                """,
                (bot_name, update_id),
            )

    def save_processed_request(
        self,
        update_id: int,
        message_id: int | None,
        status: str,
        details: str,
    ) -> None:
        # Журнал обработки полезен для отладки:
        # можно увидеть, какое сообщение было ignored/duplicate/conflict/applied.
        with self._connect() as conn:
            conn.execute(
                """
                insert into processed_requests(update_id, message_id, status, details)
                values(?, ?, ?, ?)
                on conflict(update_id) do update set
                    message_id = excluded.message_id,
                    status = excluded.status,
                    details = excluded.details
                """,
                (update_id, message_id, status, details),
            )
