from app.filters.models import ApplyResult
from app.filters.parser import FilterRequestParser


class GroupReplyFormatter:
    def __init__(self) -> None:
        self.parser = FilterRequestParser()

    def build_reply(self, text: str, result: ApplyResult) -> str | None:
        request = self.parser.parse(text)
        folder = request.target.folder_path if request else None
        values = ", ".join(request.values) if request else None

        if result.status == "applied":
            if result.related_rule and result.rendered_rule:
                return (
                    f"✅DONE - {values} - {folder}\n"
                    f"Extended existing rule:\n{result.related_rule.strip()}\n"
                    f"Updated rule:\n{result.rendered_rule.strip()}"
                )
            if values and folder:
                return f"✅DONE - {values} - {folder}"
            return "✅DONE"

        if result.status == "invalid-mailbox":
            if result.summary.startswith("mailbox not found") and folder:
                return f"Mailbox not found or named differently: {folder}"
            if result.summary.startswith("IMAP connection failed"):
                return f"Unable to connect to IMAP for mailbox validation: {result.summary}"
            if result.summary.startswith("IMAP login failed"):
                return "Unable to log in to IMAP for mailbox validation. Check the mailbox credentials."
            if result.summary.startswith("IMAP LIST failed"):
                return f"IMAP returned an error during mailbox validation: {result.summary}"
            return "Mailbox not found or named differently."

        if result.status == "duplicate":
            if result.related_rule:
                return f"Duplicate rule found: {result.summary}\nExisting rule:\n{result.related_rule.strip()}"
            return f"Duplicate rule found: {result.summary}"

        if result.status == "conflict":
            if result.related_rule:
                return f"Rule conflict: {result.summary}\nConflicting rule:\n{result.related_rule.strip()}"
            return f"Rule conflict: {result.summary}"

        if result.status == "dry-run":
            if result.related_rule and result.rendered_rule:
                return (
                    f"DRY-RUN - {values} - {folder}\n"
                    f"Would extend existing rule:\n{result.related_rule.strip()}\n"
                    f"Resulting rule:\n{result.rendered_rule.strip()}"
                )
            if values and folder:
                return f"DRY-RUN - {values} - {folder}"
            return f"DRY-RUN - {result.summary}"

        return None
