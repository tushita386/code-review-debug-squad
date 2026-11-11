"""Intent detection + routing implemented in plain Python (keyword scoring, LLM tie-break, workflow table)."""
import re
from dataclasses import dataclass

DEBUG, REVIEW, EXPLAIN, TEST = "debugging", "code_review", "code_explanation", "test_generation"
INTENTS = [DEBUG, REVIEW, EXPLAIN, TEST]

KEYWORDS = {
    DEBUG: ["bug", "fix", "error", "wrong", "not working", "doesn't work", "fails", "failing", "crash", "debug",
            "incorrect", "exception", "broken", "returns 0", "issue", "why does"],
    REVIEW: ["review", "improve", "style", "quality", "clean", "lint", "best practice", "readability",
             "refactor", "feedback", "pep"],
    EXPLAIN: ["explain", "what does", "how does", "walk through", "understand", "describe", "meaning", "teach"],
    TEST: ["test", "unit test", "test case", "pytest", "junit", "coverage"],
}

# Routing table: intent -> ordered agents (displayed in the UI and executed by the orchestrator)
WORKFLOWS = {
    DEBUG: ["Bug Finder", "Fixer", "Test Writer"],
    REVIEW: ["Bug Finder", "Style Agent", "Consolidated Report"],
    EXPLAIN: ["Explanation Handler"],
    TEST: ["Test Writer"],
}

MODE_TO_INTENT = {"Auto-detect": None, "Debugging": DEBUG, "Code review": REVIEW,
                  "Code explanation": EXPLAIN, "Test generation": TEST}
LABELS = {DEBUG: "Debugging", REVIEW: "Code review", EXPLAIN: "Code explanation", TEST: "Test generation"}


@dataclass
class IntentDecision:
    intent: str
    method: str
    reason: str


def _score(request: str):
    text = request.lower()
    return {i: sum(1 for k in kws if re.search(r"\b" + re.escape(k), text)) for i, kws in KEYWORDS.items()}


def detect_intent(request: str, forced: str = None, llm_classifier=None) -> IntentDecision:
    if forced:
        return IntentDecision(forced, "user-selected mode", f"Mode explicitly set to {LABELS[forced]}.")
    request = (request or "").strip()
    if not request:
        return IntentDecision(REVIEW, "default", "No request text, so a full code review is the safest default.")
    scores = _score(request)
    best = max(scores.values())
    leaders = [i for i, s in scores.items() if s == best]
    if best > 0 and len(leaders) == 1:
        return IntentDecision(leaders[0], "keyword scoring", f"Matched {best} keyword(s) for {LABELS[leaders[0]]}: {scores}")
    if llm_classifier:
        try:
            label = llm_classifier(request).strip().lower().replace(" ", "_")
            if label in INTENTS:
                return IntentDecision(label, "LLM classifier", "Keywords were ambiguous; Gemini classified the request.")
        except Exception:
            pass
    pick = leaders[0] if best > 0 else REVIEW
    return IntentDecision(pick, "fallback", "Ambiguous request; defaulted to " + LABELS[pick] + ".")
