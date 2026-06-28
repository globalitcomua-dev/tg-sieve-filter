import imaplib

from app.core.config import settings
from app.filters.models import MailboxTarget


class MailboxValidator:
    def validate(self, target: MailboxTarget) -> tuple[bool, str]:
        # Валидация папки сделана переключаемой через конфиг,
        # потому что в development/test среде часто нет доступа к реальному IMAP.
        if not settings.imap_validate_mailbox:
            return True, "validation disabled"

        # Можно хранить либо один общий пароль, либо карту паролей по ящикам.
        # Это удобно, если проект должен проверять папки у нескольких mailbox user'ов.
        password = settings.imap_passwords_json.get(target.mailbox_user) or settings.imap_password
        if not password:
            return False, f"missing IMAP password for {target.mailbox_user}"

        client = self._connect(target.mailbox_host)
        try:
            client.login(target.mailbox_user, password)
            status, mailboxes = client.list()
            if status != "OK":
                return False, f"LIST failed for {target.mailbox_user}@{target.mailbox_host}"

            # Множество (`set`) здесь удобно тем, что проверка
            # `target.folder_path in available` работает быстро и читаемо.
            available = {
                self._normalize_list_entry(entry.decode("utf-8", errors="ignore"))
                for entry in mailboxes or []
            }

            if target.folder_path in available:
                return True, "mailbox exists"

            return False, f"mailbox not found: {target.folder_path}"
        finally:
            try:
                # `finally` гарантирует попытку закрыть соединение,
                # даже если в середине произошла ошибка.
                client.logout()
            except Exception:
                pass

    def _connect(self, host: str):
        # Выбор между SSL и обычным IMAP — тоже через конфиг.
        if settings.imap_use_ssl:
            return imaplib.IMAP4_SSL(host, settings.imap_default_port)
        return imaplib.IMAP4(host, settings.imap_default_port)

    @staticmethod
    def _normalize_list_entry(entry: str) -> str:
        # Ответ IMAP LIST бывает немного "шумным":
        # кроме имени папки там есть служебные флаги и разделители.
        # Эта функция выдёргивает только конечный путь папки.
        if ' "/" ' in entry:
            return entry.rsplit(' "/" ', 1)[-1].strip('"')
        return entry.rsplit(" ", 1)[-1].strip('"')
