from __future__ import annotations


def _split_acronym_and_expansion(side: str) -> tuple[str, str]:
    side = side.strip()
    if not side:
        return '', ''

    if not side.endswith(')'):
        return side, ''

    depth = 0
    for index in range(len(side) - 1, -1, -1):
        char = side[index]
        if char == ')':
            depth += 1
        elif char == '(':
            depth -= 1
            if depth == 0:
                acronym = side[:index].strip()
                expansion = side[index + 1 : -1].strip()
                if acronym:
                    return acronym, expansion
                break

    return side, ''


def _find_outer_parenthetical(text: str) -> tuple[int, int] | None:
    closing_positions = [index for index, char in enumerate(text) if char == ')']
    for end in reversed(closing_positions):
        depth = 1
        for index in range(end - 1, -1, -1):
            char = text[index]
            if char == ')':
                depth += 1
            elif char == '(':
                depth -= 1
                if depth == 0:
                    return index, end
    return None


def parse_description_names(description: str) -> tuple[str, str, str, str]:
    text = (description or '').strip()
    if not text:
        return '', '', '', ''

    outer = _find_outer_parenthetical(text)
    if outer is None:
        return '', '', '', ''

    start, end = outer
    inner = text[start + 1 : end]

    depth = 0
    split_index: int | None = None
    split_length = 0
    index = 0
    while index < len(inner):
        char = inner[index]
        if char == '(':
            depth += 1
        elif char == ')':
            depth = max(0, depth - 1)
        elif depth == 0 and inner.startswith('->', index):
            split_index = index
            split_length = 2
            break
        elif depth == 0 and char == '→':
            split_index = index
            split_length = 1
            break
        index += 1

    if split_index is None:
        return '', '', '', ''

    source_side = inner[:split_index].strip()
    target_side = inner[split_index + split_length :].strip()

    source_acronym, source_expansion = _split_acronym_and_expansion(source_side)
    target_acronym, target_expansion = _split_acronym_and_expansion(target_side)
    return source_acronym, source_expansion, target_acronym, target_expansion
