"""Builds the downloadable Markdown review report."""
from datetime import datetime

from core.intent_router import LABELS

EXT = {"Python": "py", "Java": "java", "C": "c"}


def generate_report(res) -> str:
    L = EXT.get(res.language, "txt")
    s = res.summary
    out = [f"# Code Review & Debug Squad Report", f"_Generated {datetime.now():%Y-%m-%d %H:%M}_", "",
           f"**Language:** {res.language}  \n**Detected intent:** {LABELS.get(res.intent, res.intent)} ({res.intent_method})  \n"
           f"**Workflow:** {' -> '.join(res.workflow)}  \n**Verdict:** {s.get('verdict', '')}", "",
           "## Submitted Code", f"```{L}\n{res.code}\n```", ""]
    if res.request:
        out += [f"**User request:** {res.request}", ""]
    if res.explanation:
        out += ["## Code Explanation", res.explanation, ""]
    if res.bug_report:
        out += ["## Bug Analysis", res.bug_report.summary, ""]
        for b in res.bug_report.bugs:
            out += [f"### [{b.severity}] {b.title}", f"- Location: {b.line_hint or 'n/a'}", f"- Why: {b.explanation}",
                    f"- Suggested fix: {b.suggested_fix}", ""]
    if res.style_report:
        r = res.style_report
        out += ["## Style Analysis", f"**Quality score:** {r.quality_score}/10 - {r.assessment}", ""]
        out += ["**Strengths:**"] + [f"- {x}" for x in r.strengths] + ["", "**Findings:**"]
        out += [f"- ({f.category}) {f.finding} -> {f.suggestion}" for f in r.findings] + [""]
    if res.fix:
        out += ["## Corrected Code", f"```{L}\n{res.fix.fixed_code}\n```", "**Changes:**"]
        out += [f"- {c}" for c in res.fix.changes] + ["", f"**Reflection:** {res.fix.reflection}"]
        out += [f"- Remaining concern: {c}" for c in res.fix.remaining_concerns] + [""]
    if res.tests:
        out += [f"## Test Cases (run against {res.test_target})", "| # | Test | Type | Call | Expected | Actual | Status |", "|---|---|---|---|---|---|---|"]
        by_name = {r["name"]: r for r in res.test_results}
        for i, t in enumerate(res.tests, 1):
            r = by_name.get(t.name, {})
            out.append(f"| {i} | {t.name} | {t.category} | `{t.call_expression}` | `{t.expected_expression}` | "
                       f"`{r.get('actual') or r.get('error', '-')}` | {r.get('status', 'NOT RUN')} |")
        out += ["", res.exec_note] if res.exec_note else [""]
        out += [f"**Passed:** {s['tests_passed']}/{s['tests_total']}", ""]
    if res.rag_events:
        out += ["## Retrieved Knowledge (RAG)"]
        for e in res.rag_events:
            out.append(f"- **{e['agent']}**: {'retrieved ' + str(len(e['docs'])) + ' docs' if e['retrieved'] else 'no retrieval'} - {e['reason']}")
            out += [f"  - {d['source']} (similarity {d['score']})" for d in e["docs"]]
        out.append("")
    if res.errors:
        out += ["## Agent Errors"] + [f"- {k}: {v}" for k, v in res.errors.items()] + [""]
    out += ["## Recommendations"]
    recs = []
    if res.bug_report:
        recs += [f"Fix ({b.severity}): {b.suggested_fix}" for b in res.bug_report.bugs]
    if res.style_report:
        recs += [f.suggestion for f in res.style_report.findings]
    if res.fix:
        recs += res.fix.remaining_concerns
    out += [f"- {r}" for r in recs] or ["- No further recommendations."]
    return "\n".join(out)
