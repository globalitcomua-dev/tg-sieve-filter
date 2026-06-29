from app.core.config import settings
from app.filters.mailbox import MailboxValidator
from app.filters.models import MailboxTarget


def test_resolves_validation_host_from_override():
    target = MailboxTarget(
        imap_uri="imap://info%40global-it.com.ua@mail.global-it.com.ua/OFFSHORE/+Folder",
        mailbox_user="info@global-it.com.ua",
        mailbox_host="mail.global-it.com.ua",
        folder_path="OFFSHORE/+Folder",
    )
    original_override = settings.imap_validation_host_override
    settings.imap_validation_host_override = "dovecot"
    try:
        host = MailboxValidator._resolve_validation_host(target)
    finally:
        settings.imap_validation_host_override = original_override

    assert host == "dovecot"
