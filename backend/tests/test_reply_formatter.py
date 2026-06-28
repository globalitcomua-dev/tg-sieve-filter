from app.bot.reply_formatter import GroupReplyFormatter
from app.filters.models import ApplyResult


formatter = GroupReplyFormatter()


def test_formats_applied_reply():
    text = (
        "NEW\n\n"
        "d.shylenko@global-it.com.ua\n\n"
        "imap://info%40nexus.ua@mail.nexus.ua/OFFSHORE/+CSPs/GlobalIT"
    )
    result = ApplyResult(status="applied", summary="rule appended")

    reply = formatter.build_reply(text, result)

    assert reply == "✅DONE - d.shylenko@global-it.com.ua - OFFSHORE/+CSPs/GlobalIT"


def test_formats_missing_mailbox_reply():
    text = (
        "NEW\n\n"
        "d.shylenko@global-it.com.ua\n\n"
        "imap://info%40nexus.ua@mail.nexus.ua/OFFSHORE/+CSPs/GlobalIT"
    )
    result = ApplyResult(status="invalid-mailbox", summary="mailbox not found")

    reply = formatter.build_reply(text, result)

    assert reply == "Не обнаружил папку, либо она названа иначе: OFFSHORE/+CSPs/GlobalIT"


def test_formats_duplicate_reply():
    text = (
        "NEW\n\n"
        "d.shylenko@global-it.com.ua\n\n"
        "imap://info%40nexus.ua@mail.nexus.ua/OFFSHORE/+CSPs/GlobalIT"
    )
    result = ApplyResult(
        status="duplicate",
        summary="matching rule already exists for OFFSHORE/+CSPs/GlobalIT",
    )

    reply = formatter.build_reply(text, result)

    assert "Найден дубль:" in reply


def test_formats_imap_connection_reply():
    text = (
        "NEW\n\n"
        "d.shylenko@global-it.com.ua\n\n"
        "imap://info%40nexus.ua@mail.nexus.ua/OFFSHORE/+CSPs/GlobalIT"
    )
    result = ApplyResult(
        status="invalid-mailbox",
        summary="IMAP connection failed: mail.nexus.ua:993 ([Errno 111] Connection refused)",
    )

    reply = formatter.build_reply(text, result)

    assert "Не смог подключиться к IMAP" in reply
