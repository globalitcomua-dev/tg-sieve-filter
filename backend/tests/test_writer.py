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
    assert result.related_rule is None
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
    assert "already routes to OFFSHORE/+Banks/SAMPLE_BANK" in result.summary
    assert result.related_rule is not None
    assert 'fileinto "OFFSHORE/+Banks/SAMPLE_BANK";' in result.related_rule


def test_writer_extends_existing_rule_for_same_domain_and_folder(tmp_path):
    script = tmp_path / "active.sieve"
    script.write_text(
        '# rule:[+CSPs/GlobalIT]\n'
        'if address :contains ["From","To","Cc"] ["d.shylenko@global-it.com.ua"]\n'
        "{\n"
        '  fileinto "OFFSHORE/+CSPs/GlobalIT";\n'
        "  stop;\n"
        "}\n",
        encoding="utf-8",
    )
    writer = SieveScriptWriter(FileFilterStorage(script))

    original_auto_apply = settings.auto_apply
    settings.auto_apply = True
    try:
        result = writer.apply(
            make_request(
                "address",
                ["e.krashchenko@global-it.com.ua"],
                "OFFSHORE/+CSPs/GlobalIT",
            )
        )
    finally:
        settings.auto_apply = original_auto_apply

    assert result.status == "applied"
    assert result.related_rule is not None
    assert '"d.shylenko@global-it.com.ua"' in result.related_rule
    assert '"d.shylenko@global-it.com.ua","e.krashchenko@global-it.com.ua"' in result.rendered_rule
    content = script.read_text(encoding="utf-8")
    assert content.count('# rule:[+CSPs/GlobalIT]') == 1
    assert '"d.shylenko@global-it.com.ua","e.krashchenko@global-it.com.ua"' in content


def test_writer_detects_same_domain_other_folder_conflict_for_address(tmp_path):
    script = tmp_path / "active.sieve"
    script.write_text(
        '# rule:[+CSPs/GlobalIT]\n'
        'if address :contains ["From","To","Cc"] ["d.shylenko@global-it.com.ua"]\n'
        "{\n"
        '  fileinto "OFFSHORE/+CSPs/GlobalIT";\n'
        "  stop;\n"
        "}\n",
        encoding="utf-8",
    )
    writer = SieveScriptWriter(FileFilterStorage(script))

    result = writer.apply(
        make_request(
            "address",
            ["e.krashchenko@global-it.com.ua"],
            "OFFSHORE/+Clients/AnotherFolder",
        )
    )

    assert result.status == "conflict"
    assert "already routes to OFFSHORE/+CSPs/GlobalIT" in result.summary
    assert result.related_rule is not None
    assert 'fileinto "OFFSHORE/+CSPs/GlobalIT";' in result.related_rule
