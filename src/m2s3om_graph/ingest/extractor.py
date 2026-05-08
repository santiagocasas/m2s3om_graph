import re
from dataclasses import dataclass

from m2s3om_graph.models.standards import Constraint, ConstraintType, Element

LINE_RE = re.compile(r"^([A-Za-z0-9_$.:-]+)\s*[\-|:]\s*(.+)$")
CARDINALITY_RE = re.compile(r"\b(0\.\.1|0\.\.n|1\.\.1|1\.\.n|n\.\.n)\b", re.IGNORECASE)
TYPE_RE = re.compile(
    r"\b(string|text|uri|date|datetime|integer|number|boolean)\b", re.IGNORECASE
)


@dataclass
class ExtractionResult:
    elements: list[Element]


def extract_elements_from_text(standard_id: str, text: str) -> ExtractionResult:
    elements: list[Element] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = LINE_RE.match(line)
        if not match:
            continue
        path = match.group(1).strip()
        scope = match.group(2).strip()
        if path in seen:
            continue
        seen.add(path)
        constraints: list[Constraint] = []
        card = CARDINALITY_RE.search(line)
        if card:
            constraints.append(
                Constraint(kind=ConstraintType.CARDINALITY, value=card.group(1))
            )
        data_type = TYPE_RE.search(line)
        if data_type:
            constraints.append(
                Constraint(
                    kind=ConstraintType.DATATYPE, value=data_type.group(1).lower()
                )
            )
        element_id = f"{standard_id}:{path}"
        label = path.split(".")[-1]
        elements.append(
            Element(
                id=element_id,
                standard_id=standard_id,
                path=path,
                label=label,
                scope_note=scope,
                constraints=constraints,
            )
        )
    return ExtractionResult(elements=elements)
