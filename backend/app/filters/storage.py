from abc import ABC, abstractmethod
from pathlib import Path

import pymysql

from app.core.config import settings


class FilterStorage(ABC):
    # Абстрактный базовый класс задаёт "контракт":
    # любое хранилище фильтра должно уметь читать и сохранять script_data.
    #
    # Это хороший пример полиморфизма:
    # вызывающий код не знает, пишет ли он в файл или в Mailcow DB.
    @abstractmethod
    def load_script(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def save_script(self, script: str) -> str:
        raise NotImplementedError


class FileFilterStorage(FilterStorage):
    # Этот вариант полезен для локальной разработки и отладки.
    def __init__(self, script_path: Path):
        self.script_path = Path(script_path)

    def load_script(self) -> str:
        if not self.script_path.exists():
            return ""
        return self.script_path.read_text(encoding="utf-8")

    def save_script(self, script: str) -> str:
        self.script_path.parent.mkdir(parents=True, exist_ok=True)
        self.script_path.write_text(script, encoding="utf-8")
        return str(self.script_path)


class MailcowDbFilterStorage(FilterStorage):
    # Этот вариант работает с "боевым" источником истины:
    # таблицей `sieve_filters` в базе Mailcow.
    def load_script(self) -> str:
        # `with` открывает и потом автоматически закрывает соединение.
        # Это безопаснее, чем помнить о close() вручную в каждом месте.
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._select_active_filter(cursor)
                return "" if row is None or row["script_data"] is None else row["script_data"]

    def save_script(self, script: str) -> str:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._select_active_filter(cursor)
                if row is None:
                    # Если активной записи нет, создаём новую.
                    cursor.execute(
                        """
                        insert into sieve_filters
                            (username, active, filter_type, script_name, script_desc, script_data)
                        values
                            (%s, 1, %s, %s, %s, %s)
                        """,
                        (
                            settings.mailcow_filter_username,
                            settings.mailcow_filter_type,
                            settings.mailcow_filter_name,
                            settings.mailcow_filter_desc,
                            script,
                        ),
                    )
                else:
                    # Если запись уже есть, обновляем её содержимое.
                    cursor.execute(
                        """
                        update sieve_filters
                        set script_data = %s,
                            script_name = %s,
                            script_desc = %s,
                            active = 1
                        where id = %s
                        """,
                        (
                            script,
                            settings.mailcow_filter_name,
                            settings.mailcow_filter_desc,
                            row["id"],
                        ),
                    )

            # Транзакция фиксируется только после успешного SQL-блока.
            # Это защищает от частичных изменений.
            connection.commit()

        return (
            f"mailcow:sieve_filters:{settings.mailcow_filter_username}:{settings.mailcow_filter_type}"
        )

    def _select_active_filter(self, cursor) -> dict | None:
        # Выбираем последнюю активную запись нужного filter_type для нужного пользователя.
        cursor.execute(
            """
            select id, script_data
            from sieve_filters
            where username = %s
              and filter_type = %s
              and active = 1
            order by id desc
            limit 1
            """,
            (
                settings.mailcow_filter_username,
                settings.mailcow_filter_type,
            ),
        )
        return cursor.fetchone()

    @staticmethod
    def _connect():
        # Подключение вынесено в отдельную функцию, чтобы:
        # 1. не дублировать код,
        # 2. проще было менять настройки или подменять соединение в будущем.
        return pymysql.connect(
            host=settings.mailcow_db_host,
            port=settings.mailcow_db_port,
            user=settings.mailcow_db_user,
            password=settings.mailcow_db_password,
            database=settings.mailcow_db_name,
            charset="utf8mb4",
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
        )


def build_filter_storage() -> FilterStorage:
    # Простая фабрика:
    # по значению настройки выбираем конкретную реализацию storage.
    backend = settings.filter_storage_backend.lower().strip()
    if backend == "file":
        return FileFilterStorage(settings.sieve_script_path)
    if backend == "mailcow_db":
        return MailcowDbFilterStorage()
    raise ValueError(f"Unsupported FILTER_STORAGE_BACKEND: {settings.filter_storage_backend}")
