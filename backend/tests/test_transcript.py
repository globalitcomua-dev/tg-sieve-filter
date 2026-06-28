from pathlib import Path

from app.filters.parser import FilterRequestParser
from app.telegram.transcript import parse_transcript_messages


def test_parses_transcript_messages_from_fixture():
    fixture_path = Path("backend/tests/fixtures/nexus_chat_sample.txt")
    transcript = fixture_path.read_text(encoding="utf-8")

    messages = parse_transcript_messages(transcript)

    assert len(messages) == 17
    assert messages[0].author == "Ekaterina S"
    assert "@revenue.ie" in messages[0].body
    assert "OFFSHORE/+Banks/WISE" in messages[5].body


def test_extracts_filter_requests_from_transcript_fixture():
    fixture_path = Path("backend/tests/fixtures/nexus_chat_sample.txt")
    transcript = fixture_path.read_text(encoding="utf-8")

    parser = FilterRequestParser()
    requests = [
        parser.parse(message.body)
        for message in parse_transcript_messages(transcript)
    ]
    requests = [request for request in requests if request is not None]

    assert len(requests) == 9
    assert requests[0].values == ["@revenue.ie"]
    assert requests[1].values == ["@global-ags.com"]
    assert requests[2].target.folder_path == "OFFSHORE/+Banks/WISE"
    assert requests[-2].values == ["maria.stroppou@assertus.com.cy"]
    assert requests[-1].values == ["enquiries@companieshouse.gov.uk"]
