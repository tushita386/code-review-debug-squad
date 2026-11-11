"""Agent 3 - Fixer: two chained LCEL calls. (1) draft fix, (2) REFLECTION pass that critiques and finalises the draft."""
from core.chains import build_chain, run_chain
from core.prompts import FIX_DRAFT_PROMPT, FIX_REFLECT_PROMPT
from core.schemas import FixDraft, FixResult


def run(language: str, code: str, bug_text: str, style_text: str, context: str) -> FixResult:
    draft = run_chain(build_chain(FIX_DRAFT_PROMPT, FixDraft), {
        "language": language.lower(), "code": code, "bug_report": bug_text,
        "style_report": style_text, "context": context})
    try:  # reflection step; if it fails we still return the draft
        return run_chain(build_chain(FIX_REFLECT_PROMPT, FixResult), {
            "language": language.lower(), "code": code, "bug_report": bug_text,
            "draft_code": draft.fixed_code, "draft_changes": "\n".join(draft.changes)})
    except Exception as exc:
        return FixResult(fixed_code=draft.fixed_code, changes=draft.changes,
                         reflection=f"Reflection step unavailable ({exc}); draft returned unchanged.",
                         remaining_concerns=[])
