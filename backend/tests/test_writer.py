from app.core.config import settings
from app.filters.models import FilterRequest, MailboxTarget
from app.filters.storage import FileFilterStorage
from app.filters.writer import SieveScriptWriter


def make_request(match_type: str, values: list[str], folder_path: str) -> FilterRequest:
    return FilterRequest(
        original_text="",
        target=MailboxTarget(
            imap_uri="imap://info%40global-it.com.ua@mail.global-it.com.ua/" + folder_path,
            mailbox_user="info@global-it.com.ua",
            mailbox_host="mail.global-it.com.ua",
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
                ["inbox@sample-registry.example"],
                "OFFSHORE/+Vendors/UNITED_KINGDOM/Sample_Registry",
            )
        )
    finally:
        settings.auto_apply = original_auto_apply

    assert result.status == "applied"
    content = script.read_text(encoding="utf-8")
    assert 'fileinto "OFFSHORE/+Vendors/UNITED_KINGDOM/Sample_Registry";' in content
    assert '"inbox@sample-registry.example"' in content


def test_writer_detects_domain_conflict(tmp_path):
    script = tmp_path / "active.sieve"
    script.write_text(
        '# rule:[+Banks/SAMPLE_BANK]\n'
        'if address :contains ["From","To","Cc"] ["@samplebank.example"]\n'
        "{\n"
        '  fileinto "OFFSHORE/+Banks/SAMPLE_BANK";\n'
        "  stop;\n"
        "}\n",
        encoding="utf-8",
    )
    writer = SieveScriptWriter(FileFilterStorage(script))

    result = writer.apply(
        make_request(
            "domain",
            ["@samplebank.example"],
            "OFFSHORE/+Vendors/ANOTHER/Sample_Bank",
        )
    )

    assert result.status == "conflict"
    assert "already exists" in result.summary
