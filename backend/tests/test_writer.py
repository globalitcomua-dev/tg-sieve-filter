from app.core.config import settings
from app.filters.models import FilterRequest, MailboxTarget
from app.filters.storage import FileFilterStorage
from app.filters.writer import SieveScriptWriter


def make_request(match_type: str, values: list[str], folder_path: str) -> FilterRequest:
    return FilterRequest(
        original_text="",
        target=MailboxTarget(
            imap_uri="imap://info%40nexus.ua@mail.nexus.ua/" + folder_path,
            mailbox_user="info@nexus.ua",
            mailbox_host="mail.nexus.ua",
            folder_path=folder_path,
        ),
        match_type=match_type,
        values=values,
    )


def test_writer_appends_rule(tmp_path):
    script = tmp_path / "active.sieve"
    writer = SieveScriptWriter(FileFilterStorage(script))

    original_auto_apply = settings.auto_apply
    settings.auto_apply = True
    try:
        result = writer.apply(
            make_request(
                "address",
                ["enquiries@companieshouse.gov.uk"],
                "OFFSHORE/+CSPs/UNITED_KINGDOM/Companies_House_UK",
            )
        )
    finally:
        settings.auto_apply = original_auto_apply

    assert result.status == "applied"
    content = script.read_text(encoding="utf-8")
    assert 'fileinto "OFFSHORE/+CSPs/UNITED_KINGDOM/Companies_House_UK";' in content
    assert '"enquiries@companieshouse.gov.uk"' in content


def test_writer_detects_domain_conflict(tmp_path):
    script = tmp_path / "active.sieve"
    script.write_text(
        '# rule:[+Banks/WISE]\n'
        'if address :contains ["From","To","Cc"] ["@wise.com"]\n'
        "{\n"
        '  fileinto "OFFSHORE/+Banks/WISE";\n'
        "  stop;\n"
        "}\n",
        encoding="utf-8",
    )
    writer = SieveScriptWriter(FileFilterStorage(script))

    result = writer.apply(
        make_request(
            "domain",
            ["@wise.com"],
            "OFFSHORE/+CSPs/ANOTHER/Wise",
        )
    )

    assert result.status == "conflict"
    assert "already exists" in result.summary
