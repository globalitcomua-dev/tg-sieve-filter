from app.filters.parser import FilterRequestParser


def test_parses_domain_request_with_imap_target():
    parser = FilterRequestParser()

    request = parser.parse(
        "[18.12.2025 14:36] Ekaterina S: New OSSNSD@revenue.ie "
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
        "[18.05.2026 12:22] Legal Assistant Nexus: NEW "
        "(i.zammit@sheltonsgroup.com.mt), (f.sant@sheltonsgroup.com.mt), "
        "(j.fenech@sheltonsgroup.com.mt), (p.narwani@sheltonsgroup.com.mt) "
        "imap://info%40nexus.ua@mail.nexus.ua/OFFSHORE/+CSPs/MALTA/Paul McKenna"
    )

    assert request is not None
    assert request.match_type == "address"
    assert request.values == [
        "i.zammit@sheltonsgroup.com.mt",
        "f.sant@sheltonsgroup.com.mt",
        "j.fenech@sheltonsgroup.com.mt",
        "p.narwani@sheltonsgroup.com.mt",
    ]
    assert request.target.mailbox_user == "info@nexus.ua"
    assert request.target.folder_path == "OFFSHORE/+CSPs/MALTA/Paul McKenna"


def test_normalizes_whitespace_inside_folder_path():
    parser = FilterRequestParser()

    request = parser.parse(
        "[18.05.2026 12:47] Legal Assistant Nexus: NEW bangkokmastery@gmail.com "
        "imap://post%40nexus.ua@mail/OFFSHORE/+Clients/ Kentaro"
    )

    assert request is not None
    assert request.target.folder_path == "OFFSHORE/+Clients/Kentaro"
