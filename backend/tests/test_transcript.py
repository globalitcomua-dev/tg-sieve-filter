from pathlib import Path

from app.filters.parser import FilterRequestParser
from app.telegram.transcript import parse_transcript_messages


def test_parses_transcript_messages_from_fixture():
    transcript = Path("backend/tests/fixtures/chat_sample.txt").read_text(encoding="utf-8")
    messages = parse_transcript_messages(transcript)

    assert len(messages) == 17
    assert messages[0].author == "Olivia Hart"
    assert "@revenue.ie" in messages[0].body
    assert "OFFSHORE/+Banks/SAMPLE_BANK" in messages[5].body


def test_extracts_filter_requests_from_transcript_fixture():
    transcript = Path("backend/tests/fixtures/chat_sample.txt").read_text(encoding="utf-8")
    parser = FilterRequestParser()
    requests = [
        parser.parse(message.body)
        for message in parse_transcript_messages(transcript)
    ]
    requests = [request for request in requests if request is not None]

    assert len(requests) == 9
    assert requests[0].values == ["@revenue.ie"]
    assert requests[1].values == ["@global-ags.com"]
    assert requests[2].target.folder_path == "OFFSHORE/+Banks/SAMPLE_BANK"
    assert requests[-2].values == ["maria.stone@sampleadvisors.example"]
    assert requests[-1].values == ["inbox@sample-registry.example"]
