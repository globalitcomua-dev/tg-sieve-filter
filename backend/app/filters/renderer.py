from app.core.config import settings
from app.filters.models import FilterRequest


class SieveRuleRenderer:
    def render(self, request: FilterRequest) -> str:
        values = ",".join(f'"{value}"' for value in request.values)
        comment_label = request.target.folder_path.removeprefix("OFFSHORE/")

        return (
            f'{settings.rule_comment_prefix}[{comment_label}]\n'
            f'if address :contains ["From","To","Cc"] [{values}]\n'
            "{\n"
            f'  fileinto "{request.target.folder_path}";\n'
            "  stop;\n"
            "}\n"
        )
