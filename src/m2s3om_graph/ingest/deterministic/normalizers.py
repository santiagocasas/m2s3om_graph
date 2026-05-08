import re

_RTF_HEX_ESCAPE_RE = re.compile(r"\\'[0-9a-fA-F]{2}")
_RTF_CONTROL_WORD_RE = re.compile(r"\\[a-zA-Z]+-?\d* ?")
_SPACE_RE = re.compile(r"[ \t]+")


def normalize_text_for_deterministic(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _RTF_HEX_ESCAPE_RE.sub(" ", cleaned)
    cleaned = cleaned.replace("\\par", "\n")
    cleaned = _RTF_CONTROL_WORD_RE.sub(" ", cleaned)
    cleaned = (
        cleaned.replace("{", " ")
        .replace("}", " ")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2192", "->")
    )

    out_lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = _SPACE_RE.sub(" ", raw_line).strip()
        if line:
            out_lines.append(line)
    return "\n".join(out_lines)
