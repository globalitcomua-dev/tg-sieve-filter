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

    assert reply == "Mailbox not found or named differently: OFFSHORE/+CSPs/GlobalIT"


def test_formats_duplicate_reply():
    text = (
        "NEW\n\n"
        "d.shylenko@global-it.com.ua\n\n"
        "imap://info%40nexus.ua@mail.nexus.ua/OFFSHORE/+CSPs/GlobalIT"
    )
    result = ApplyResult(
        status="duplicate",
        summary="matching rule already exists for OFFSHORE/+CSPs/GlobalIT",
        related_rule=(
            '# rule:[+CSPs/GlobalIT]\n'
            'if address :contains ["From","To","Cc"] ["d.shylenko@global-it.com.ua"]\n'
            "{\n"
            '  fileinto "OFFSHORE/+CSPs/GlobalIT";\n'
            "  stop;\n"
            "}\n"
        ),
    )

    reply = formatter.build_reply(text, result)

    assert "Duplicate rule found:" in reply
    assert "Existing rule:" in reply
    assert 'fileinto "OFFSHORE/+CSPs/GlobalIT";' in reply


def test_formats_conflict_reply_with_rule_body():
    text = (
        "NEW\n\n"
        "e.krashchenko@global-it.com.ua\n\n"
        "imap://info%40nexus.ua@mail.nexus.ua/OFFSHORE/+Clients/AnotherFolder"
    )
    result = ApplyResult(
        status="conflict",
        summary="domain @global-it.com.ua already routes to OFFSHORE/+CSPs/GlobalIT",
        related_rule=(
            '# rule:[+CSPs/GlobalIT]\n'
            'if address :contains ["From","To","Cc"] ["d.shylenko@global-it.com.ua"]\n'
            "{\n"
            '  fileinto "OFFSHORE/+CSPs/GlobalIT";\n'
            "  stop;\n"
            "}\n"
        ),
    )

    reply = formatter.build_reply(text, result)

    assert "Rule conflict:" in reply
    assert "Conflicting rule:" in reply
    assert 'fileinto "OFFSHORE/+CSPs/GlobalIT";' in reply


def test_formats_applied_extension_reply_with_before_and_after():
    text = (
        "NEW\n\n"
        "e.krashchenko@global-it.com.ua\n\n"
        "imap://info%40nexus.ua@mail.nexus.ua/OFFSHORE/+CSPs/GlobalIT"
    )
    result = ApplyResult(
        status="applied",
        summary="rule extended",
        related_rule=(
            '# rule:[+CSPs/GlobalIT]\n'
            'if address :contains ["From","To","Cc"] ["d.shylenko@global-it.com.ua"]\n'
            "{\n"
            '  fileinto "OFFSHORE/+CSPs/GlobalIT";\n'
            "  stop;\n"
            "}\n"
        ),
        rendered_rule=(
            '# rule:[+CSPs/GlobalIT]\n'
            'if address :contains ["From","To","Cc"] ["d.shylenko@global-it.com.ua","e.krashchenko@global-it.com.ua"]\n'
            "{\n"
            '  fileinto "OFFSHORE/+CSPs/GlobalIT";\n'
            "  stop;\n"
            "}\n"
        ),
    )

    reply = formatter.build_reply(text, result)

    assert "Extended existing rule:" in reply
    assert "Updated rule:" in reply
    assert '"d.shylenko@global-it.com.ua","e.krashchenko@global-it.com.ua"' in reply


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

    assert "Unable to connect to IMAP" in reply
