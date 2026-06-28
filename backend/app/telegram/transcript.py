from dataclasses import dataclass
import re


MESSAGE_START_RE = re.compile(
    r"^\[(?P<date>\d{2}\.\d{2}\.\d{4}\s+\d{1,2}:\d{2})\]\s+(?P<author>[^:]+):\s?(?P<body>.*)$"
)


@dataclass(slots=True)
class TranscriptMessage:
    date: str
    author: str
    body: str


def parse_transcript_messages(text: str) -> list[TranscriptMessage]:
    messages: list[TranscriptMessage] = []
    current_date: str | None = None
    current_author: str | None = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        match = MESSAGE_START_RE.match(line)
        if match:
            if current_date is not None and current_author is not None:
                messages.append(
                    TranscriptMessage(
                        date=current_date,
                        author=current_author,
                        body="\n".join(current_lines).strip(),
                    )
                )
            current_date = match.group("date")
            current_author = match.group("author").strip()
            current_lines = [match.group("body")]
            continue

        if current_date is not None:
            current_lines.append(line)

    if current_date is not None and current_author is not None:
        messages.append(
            TranscriptMessage(
                date=current_date,
                author=current_author,
                body="\n".join(current_lines).strip(),
            )
        )

    return messages
