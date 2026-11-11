"""Orchestrator: routes the request to the right agents and passes each agent's output to the next."""
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agents import bug_finder, fixer_agent, style_agent, test_writer
from core.chains import explain_code, intent_chain
from core.intent_router import DEBUG, EXPLAIN, LABELS, MODE_TO_INTENT, REVIEW, TEST, WORKFLOWS, detect_intent
from core.llm import explain_error
from rag.retriever import decide_retrieval, format_context, retrieve

SUPPORTED_LANGUAGES = ["Python", "Java", "C"]


@dataclass
class SquadResult:
    language: str
    code: str
    request: str
    intent: str = ""
    intent_method: str = ""
    intent_reason: str = ""
    workflow: List[str] = field(default_factory=list)
    bug_report: Any = None
    style_report: Any = None
    fix: Any = None
    tests: List[Any] = field(default_factory=list)
    test_results: List[Dict] = field(default_factory=list)
    baseline_results: List[Dict] = field(default_factory=list)  # same tests on the ORIGINAL code
    test_target: str = "original code"
    exec_note: str = ""
    explanation: str = ""
    rag_events: List[Dict] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    trace: List[Dict] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)


def _step(res: SquadResult, name: str, fn, progress=None):
    """Run one agent; failures are recorded and never crash the workflow."""
    if progress:
        progress(f"{name} working...")
    t0 = time.time()
    try:
        out = fn()
        res.trace.append({"step": name, "status": "ok", "seconds": round(time.time() - t0, 1)})
        return out
    except Exception as exc:
        res.errors[name] = explain_error(exc)
        res.trace.append({"step": name, "status": "failed", "seconds": round(time.time() - t0, 1)})
        return None


def _context(res: SquadResult, agent: str, query: str) -> str:
    """Agentic RAG: decide first, then retrieve (or skip)."""
    use, reason = decide_retrieval(agent, res.intent, res.request)
    event = {"agent": agent, "retrieved": False, "reason": reason, "query": query, "docs": []}
    docs = []
    if use:
        try:
            docs = retrieve(query, res.language)
            event.update(retrieved=True, docs=docs)
        except Exception as exc:
            event["reason"] += f" (retrieval failed: {type(exc).__name__}: {str(exc)[:120]})"
    res.rag_events.append(event)
    return format_context(docs)


def _bug_text(res):
    if not res.bug_report:
        return "(no bug report available)"
    lines = [res.bug_report.summary] + [
        f"- [{b.severity}] {b.title}: {b.explanation} Fix: {b.suggested_fix}" for b in res.bug_report.bugs]
    return "\n".join(lines)


def _style_text(res):
    if not res.style_report:
        return "(not requested in this workflow)"
    return "\n".join(f"- ({f.category}) {f.finding} -> {f.suggestion}" for f in res.style_report.findings) or "(no style issues)"


def _test_phase(res: SquadResult, progress):
    target = res.fix.fixed_code if res.fix else res.code
    res.test_target = "fixed code" if res.fix else "original code"
    ctx = _context(res, "test_writer", f"unit testing edge cases boundary {res.language} {res.request}")
    suite = _step(res, "Test Writer", lambda: test_writer.run(res.language, target, res.request, ctx), progress)
    if not suite:
        return
    res.tests = suite.tests
    if res.language == "Python":
        _step(res, "Test Execution (sandbox)", lambda: setattr(res, "test_results", test_writer.execute(res.tests, target)), progress)
        if res.fix:
            res.baseline_results = test_writer.execute(res.tests, res.code)
    else:
        res.exec_note = (f"{res.language} tests were generated but NOT executed: the restricted executor supports "
                         "Python only. Expected values are shown without pretending they were run.")


def build_summary(res: SquadResult) -> Dict:
    bugs = res.bug_report.bugs if res.bug_report else []
    findings = res.style_report.findings if res.style_report else []
    passed = sum(r["status"] == "PASS" for r in res.test_results)
    sev = {s: sum(b.severity == s for b in bugs) for s in ("Critical", "High", "Medium", "Low")}
    if res.intent == EXPLAIN:
        verdict = "Explanation generated."
    elif res.intent == TEST:
        verdict = "Tests generated." + (f" {passed}/{len(res.test_results)} passed." if res.test_results else "")
    elif sev["Critical"] or sev["High"]:
        verdict = "Needs attention: serious defects found."
    elif bugs:
        verdict = "Mostly sound: minor defects found."
    elif res.bug_report:
        verdict = "Looks healthy: no functional bugs found."
    else:
        verdict = "Incomplete: the bug analysis did not run."
    return {"bugs": len(bugs), "style_findings": len(findings), "severity": sev, "tests_total": len(res.test_results),
            "tests_passed": passed, "tests_generated": len(res.tests), "verdict": verdict,
            "quality_score": res.style_report.quality_score if res.style_report else None}


def run_squad(language: str, code: str, request: str, mode: str = "Auto-detect", progress=None) -> SquadResult:
    if not code or not code.strip():
        raise ValueError("Please paste some code (or click 'Load sample') before analysing.")
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language '{language}'. Choose one of: {', '.join(SUPPORTED_LANGUAGES)}.")
    res = SquadResult(language=language, code=code, request=(request or "").strip())

    decision = detect_intent(res.request, MODE_TO_INTENT.get(mode),
                             lambda r: intent_chain().invoke({"request": r}))
    res.intent, res.intent_method, res.intent_reason = decision.intent, decision.method, decision.reason
    res.workflow = WORKFLOWS[res.intent]
    if progress:
        progress(f"Detected intent: {LABELS[res.intent]} ({decision.method})")

    snippet = res.code[:300]
    if res.intent == EXPLAIN:
        ctx = _context(res, "explainer", f"{res.request} {res.language}")
        res.explanation = _step(res, "Explanation Handler",
                                lambda: explain_code(res.language, res.code, res.request, ctx), progress) or ""
    elif res.intent == TEST:
        _test_phase(res, progress)
    else:
        ctx = _context(res, "bug_finder", f"common bugs edge cases debugging {res.language} {res.request} {snippet}")
        res.bug_report = _step(res, "Bug Finder", lambda: bug_finder.run(res.language, res.code, res.request, ctx), progress)
        if res.intent == REVIEW:
            ctx = _context(res, "style", f"{res.language} coding style naming conventions readability")
            res.style_report = _step(res, "Style Agent", lambda: style_agent.run(res.language, res.code, res.request, ctx), progress)
        else:  # DEBUG: Bug Finder -> Fixer -> Test Writer
            ctx = _context(res, "fixer", f"fix {res.language} bug " + " ".join(b.title for b in (res.bug_report.bugs if res.bug_report else [])))
            res.fix = _step(res, "Fixer Agent", lambda: fixer_agent.run(res.language, res.code, _bug_text(res), _style_text(res), ctx), progress)
            _test_phase(res, progress)
    res.summary = build_summary(res)
    return res
