"""Custom MkDocs extension to handle code anchor format: ```start:end:filepath"""

import re
from pathlib import Path

from markdown import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor


class CodeAnchorPreprocessor(Preprocessor):
    """Preprocess code blocks with anchor format: ```start:end:filepath"""

    def __init__(self, md: Markdown, base_path: Path):
        super().__init__(md)
        self.base_path = base_path
        self.pattern = re.compile(r"^```(\d+):(\d+):([^\n]+)\n(.*?)```$", re.MULTILINE | re.DOTALL)

    def run(self, lines: list[str]) -> list[str]:
        """Process lines and convert code anchor format to standard code blocks."""
        text = "\n".join(lines)
        new_text = self.pattern.sub(self._replace_code_anchor, text)
        return new_text.split("\n")

    def _replace_code_anchor(self, match) -> str:
        """Replace code anchor format with standard code block + link."""
        start_line = int(match.group(1))
        end_line = int(match.group(2))
        file_path = match.group(3).strip()
        existing_code = match.group(4)

        # Determine language from file extension
        ext = Path(file_path).suffix.lower()
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".md": "markdown",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".json": "json",
            ".html": "html",
            ".css": "css",
            ".sh": "bash",
        }
        language = lang_map.get(ext, "python")

        # Generate GitHub link
        repo_url = "https://github.com/DeepCritical/GradioDemo"
        github_link = f"{repo_url}/blob/main/{file_path}#L{start_line}-L{end_line}"

        # Return standard code block with source link
        return (
            f'[View source: `{file_path}` (lines {start_line}-{end_line})]({github_link}){{: target="_blank" }}\n\n'
            f"```{language}\n{existing_code}\n```"
        )


class CodeAnchorExtension(Extension):
    """Markdown extension for code anchors."""

    def __init__(self, base_path: str = ".", **kwargs):
        super().__init__(**kwargs)
        self.base_path = Path(base_path)

    def extendMarkdown(self, md: Markdown):  # noqa: N802
        """Register the preprocessor."""
        md.preprocessors.register(CodeAnchorPreprocessor(md, self.base_path), "codeanchor", 25)


def makeExtension(**kwargs):  # noqa: N802
    """Create the extension."""
    return CodeAnchorExtension(**kwargs)
