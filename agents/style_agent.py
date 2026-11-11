"""Agent 2 - Style and Lint Agent: LCEL chain -> StyleReport."""
from core.chains import build_chain, run_chain
from core.prompts import STYLE_PROMPT
from core.schemas import StyleReport


def run(language: str, code: str, request: str, context: str) -> StyleReport:
    chain = build_chain(STYLE_PROMPT, StyleReport)
    return run_chain(chain, {"language": language.lower(), "code": code,
                             "request": request or "Review code style.", "context": context})
