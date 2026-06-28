from app.filters.parser import FilterRequestParser


def test_parses_domain_request_with_imap_target():
    parser = FilterRequestParser()

    request = parser.parse(
        "[18.12.2025 14:36] Olivia Hart: New OSSNSD@revenue.ie "
        "(и любые адреса с @revenue.ie ) to "
        "imap://post@mail/OFFSHORE/+CSPs/Ireland/ROS"
    )

    assert request is not None
    assert request.match_type == "domain"
    assert request.values == ["@revenue.ie"]
    assert request.target.mailbox_user == "post"
    assert request.target.folder_path == "OFFSHORE/+CSPs/Ireland/ROS"


def test_parses_multiple_address_request():
    parser = FilterRequestParser()

    request = parser.parse(
        "[18.05.2026 12:22] Legal Assistant Fexus: NEW "
        "(ira.lee@samplegroup.example), (felix.sant@samplegroup.example), "
        "(jane.finch@samplegroup.example), (paul.north@samplegroup.example) "
        "imap://info%40global-it.com.ua@mail.global-it.com.ua/OFFSHORE/+Vendors/MALTA/Sample_Advisor"
    )

    assert request is not None
    assert request.match_type == "address"
    assert request.values == [
        "ira.lee@samplegroup.example",
        "felix.sant@samplegroup.example",
        "jane.finch@samplegroup.example",
        "paul.north@samplegroup.example",
    ]
    assert request.target.mailbox_user == "info@global-it.com.ua"
    assert request.target.folder_path == "OFFSHORE/+Vendors/MALTA/Sample_Advisor"


def test_normalizes_whitespace_inside_folder_path():
    parser = FilterRequestParser()

    request = parser.parse(
        "[18.05.2026 12:47] Legal Assistant Fexus: NEW skyreader@example.com "
        "imap://post%40global-it.com.ua@mail/OFFSHORE/+Clients/ Example Client"
    )

    assert request is not None
    assert request.target.folder_path == "OFFSHORE/+Clients/Example Client"
