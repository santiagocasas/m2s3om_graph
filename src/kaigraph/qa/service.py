from kaigraph.db import CrosswalkRepository


def answer_question(repo: CrosswalkRepository, question: str) -> str:
    lower = question.lower()
    chunks = repo.all_chunks()
    ranked = [
        x for x in chunks if any(token in x.content.lower() for token in lower.split())
    ]
    if not ranked:
        return "No grounded evidence found in standards corpus."
    top = ranked[:3]
    evidence = "\n\n".join(f"- {x.content[:220]}" for x in top)
    return f"Grounded answer candidate based on standards corpus:\n\n{evidence}"
