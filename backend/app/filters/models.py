from dataclasses import dataclass


@dataclass(slots=True)
class MailboxTarget:
    imap_uri: str
    mailbox_user: str
    mailbox_host: str
    folder_path: str


@dataclass(slots=True)
class FilterRequest:
    original_text: str
    target: MailboxTarget
    match_type: str
    values: list[str]
    source_hint: str | None = None


@dataclass(slots=True)
class ApplyResult:
    status: str
    summary: str
    rendered_rule: str | None = None
