"""Agent 1 - Bug Finder: LCEL chain  prompt | gemini | parser -> BugReport."""
from core.chains import build_chain, run_chain
from core.prompts import BUG_PROMPT
from core.schemas import BugReport


def run(language: str, code: str, request: str, context: str) -> BugReport:
    chain = build_chain(BUG_PROMPT, BugReport)
    return run_chain(chain, {"language": language.lower(), "code": code,
                             "request": request or "Find bugs.", "context": context})
