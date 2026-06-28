import imaplib
import logging

from app.core.config import settings
from app.filters.models import MailboxTarget


logger = logging.getLogger(__name__)


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
            logger.warning("IMAP validation failed: missing password for mailbox_user=%s", target.mailbox_user)
            return False, f"missing IMAP password for {target.mailbox_user}"

        logger.info(
            "IMAP validation started: mailbox_user=%s mailbox_host=%s folder_path=%s ssl=%s port=%s",
            target.mailbox_user,
            target.mailbox_host,
            target.folder_path,
            settings.imap_use_ssl,
            settings.imap_default_port,
        )

        client = self._connect(target.mailbox_host)
        try:
            logger.info("IMAP connected: host=%s", target.mailbox_host)
            client.login(target.mailbox_user, password)
            logger.info("IMAP login succeeded: mailbox_user=%s", target.mailbox_user)
            status, mailboxes = client.list()
            if status != "OK":
                logger.warning(
                    "IMAP LIST failed: mailbox_user=%s mailbox_host=%s status=%s",
                    target.mailbox_user,
                    target.mailbox_host,
                    status,
                )
                return False, f"LIST failed for {target.mailbox_user}@{target.mailbox_host}"

            # Множество (`set`) здесь удобно тем, что проверка
            # `target.folder_path in available` работает быстро и читаемо.
            available = {
                self._normalize_list_entry(entry.decode("utf-8", errors="ignore"))
                for entry in mailboxes or []
            }
            logger.info(
                "IMAP LIST succeeded: mailbox_user=%s mailboxes_found=%s",
                target.mailbox_user,
                len(available),
            )

            if target.folder_path in available:
                logger.info(
                    "IMAP mailbox exists: mailbox_user=%s folder_path=%s",
                    target.mailbox_user,
                    target.folder_path,
                )
                return True, "mailbox exists"

            logger.warning(
                "IMAP mailbox not found: mailbox_user=%s folder_path=%s sample=%s",
                target.mailbox_user,
                target.folder_path,
                sorted(available)[:10],
            )
            return False, f"mailbox not found: {target.folder_path}"
        finally:
            try:
                # `finally` гарантирует попытку закрыть соединение,
                # даже если в середине произошла ошибка.
                client.logout()
                logger.info("IMAP logout succeeded: mailbox_user=%s", target.mailbox_user)
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
