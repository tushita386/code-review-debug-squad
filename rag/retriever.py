"""Agentic retrieval: the workflow DECIDES whether to retrieve, then runs similarity search."""
from .vector_store import get_store

# Which agents benefit from retrieval for which intent
RETRIEVAL_POLICY = {
    "bug_finder": ({"debugging", "code_review"}, "debugging guidelines and known bug patterns"),
    "style": ({"code_review"}, "language-specific coding standards"),
    "fixer": ({"debugging"}, "fix patterns and defensive-programming advice"),
    "test_writer": ({"debugging", "test_generation"}, "testing guidelines for edge/boundary cases"),
    "explainer": (set(), "explanations are answered from the model's own knowledge"),
}
KNOWLEDGE_WORDS = ("best practice", "guideline", "convention", "standard", "pep", "idiom", "complexity", "big o")


def decide_retrieval(agent: str, intent: str, request: str):
    """Return (should_retrieve, reason). Pure Python decision, shown in the UI."""
    intents, what = RETRIEVAL_POLICY[agent]
    if intent in intents:
        return True, f"Intent '{intent}' benefits from {what}."
    if any(w in (request or "").lower() for w in KNOWLEDGE_WORDS):
        return True, "Request explicitly asks for best practices / standards."
    return False, f"Skipped: intent '{intent}' does not need external knowledge for the {agent.replace('_', ' ')}."


def retrieve(query: str, language: str, k: int = 3):
    """Similarity search filtered to the chosen language + language-agnostic docs."""
    flt = {"language": {"$in": [language.lower(), "general"]}}
    hits = get_store().similarity_search_with_score(query, k=k, filter=flt)
    results = []
    for doc, dist in hits:
        results.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "?"),
            "topic": doc.metadata.get("topic", "?"),
            "language": doc.metadata.get("language", "?"),
            "type": doc.metadata.get("type", "?"),
            "score": round(1 - float(dist), 3),  # cosine similarity
        })
    return results


def format_context(docs) -> str:
    if not docs:
        return "(none)"
    return "\n".join(f"[{i}] ({d['source']}) {d['content']}" for i, d in enumerate(docs, 1))
