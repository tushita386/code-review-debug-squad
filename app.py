"""Code Review & Debug Squad - Streamlit UI."""
from pathlib import Path

import streamlit as st

from core.intent_router import LABELS, MODE_TO_INTENT
from core.llm import api_key, explain_error, model_name
from core.orchestrator import SUPPORTED_LANGUAGES, run_squad
from tools.report_generator import EXT, generate_report

st.set_page_config(page_title="Code Review & Debug Squad", page_icon="🛡️", layout="wide")
css = Path(__file__).parent / "assets" / "style.css"
st.markdown(f"<style>{css.read_text()}</style>", unsafe_allow_html=True)

SAMPLE_CODE = """def find_max(arr):
    max_num = 0
    for num in arr:
        if num > max_num:
            max_num = num
    return max_num
"""
SAMPLE_REQUEST = "Why does this return 0 for negative numbers? Find and fix the bug."
PAGES = {"🏠 Dashboard": "Auto-detect", "🐞 Code Debugger": "Debugging", "🔍 Code Review": "Code review",
         "📖 Code Explanation": "Code explanation", "🧪 Test Generator": "Test generation", "ℹ️ About Project": None}
STATUS_ICON = {"PASS": "✅ PASS", "FAIL": "❌ FAIL", "ERROR": "⚠️ ERROR", "TIMEOUT": "⏱️ TIMEOUT"}

st.session_state.setdefault("code_input", "")
st.session_state.setdefault("request_input", "")


def load_sample():
    st.session_state.update(code_input=SAMPLE_CODE, request_input=SAMPLE_REQUEST, lang_input="Python")


# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("## 🛡️ Code Squad")
    st.caption("Multi-agent AI code assistant")
    page = st.radio("Navigation", list(PAGES), label_visibility="collapsed")
    st.divider()
    if api_key():
        st.success(f"Gemini key loaded\n\nModel: `{model_name()}`")
    else:
        st.error("No GOOGLE_API_KEY found. Copy `.env.example` to `.env`, add your key, restart.")
    st.caption("Agents: Bug Finder · Style · Fixer · Test Writer\n\nLangChain · LCEL · ChromaDB · HuggingFace")


# ---------------- About page ----------------
def about():
    st.markdown("<div class='hero'><h1>About Code Review & Debug Squad</h1></div>", unsafe_allow_html=True)
    st.markdown("""
A multi-agent assistant: **Bug Finder → Style Agent → Fixer (with reflection) → Test Writer**, orchestrated in Python.

| # | Acceptance criterion | Where |
|---|---|---|
| 1 | LLM integration (Gemini) | `core/llm.py` |
| 2 | Interactive GUI | `app.py` |
| 3 | Prompt engineering | `core/prompts.py` |
| 4 | LangChain + LCEL | `core/chains.py`, `agents/` |
| 5 | Agentic RAG | `rag/retriever.py` (`decide_retrieval`) |
| 6 | Intent routing | `core/intent_router.py`, `core/orchestrator.py` |
| 7 | ChromaDB | `rag/vector_store.py` |
""")
    st.subheader("Knowledge stored in ChromaDB")
    if st.button("Inspect vector database"):
        try:
            with st.spinner("Loading embeddings model (first run downloads ~90 MB)..."):
                from rag.vector_store import list_documents
                docs = list_documents()
            st.success(f"{len(docs)} documents stored in persistent ChromaDB")
            st.dataframe([{k: d[k] for k in ("id", "language", "topic", "type", "source")} for d in docs], use_container_width=True)
        except Exception as exc:
            st.error(f"Vector DB unavailable: {exc}")


if page == "ℹ️ About Project":
    about()
    st.stop()

# ---------------- Input section ----------------
st.markdown("<div class='hero'><h1>Your AI-Powered Code Review Team</h1>"
            "<p>Four specialized AI agents. One smarter code review.</p></div>", unsafe_allow_html=True)

modes = list(MODE_TO_INTENT)
c1, c2, c3 = st.columns([1, 1, 1])
language = c1.selectbox("Programming language", SUPPORTED_LANGUAGES, key="lang_input")
mode = c2.selectbox("Analysis mode", modes, index=modes.index(PAGES[page]), key=f"mode_{page}")
c3.write("")
c3.button("⚡ Load sample (find_max)", on_click=load_sample, use_container_width=True)

st.text_area("Code editor", key="code_input", height=280, placeholder="Paste your code here...")
st.text_input("What do you need?", key="request_input", placeholder="e.g. Find the bug and fix it / Explain this code / Write tests")
go = st.button("🚀 Analyze Code", type="primary")

if go:
    if not api_key():
        st.error("Gemini API key missing. Add GOOGLE_API_KEY to your `.env` file and restart Streamlit.")
    else:
        try:
            with st.status("Squad is working...", expanded=True) as status:
                res = run_squad(language, st.session_state.code_input, st.session_state.request_input, mode,
                                progress=lambda m: st.write("•", m))
                status.update(label="Analysis complete", state="complete", expanded=False)
            st.session_state["result"] = res
        except ValueError as exc:
            st.warning(str(exc))
        except Exception as exc:
            st.error(explain_error(exc))

res = st.session_state.get("result")
if not res:
    st.info("Load the sample or paste code, then click **Analyze Code**.")
    st.stop()

# ---------------- Results ----------------
s = res.summary
st.markdown("### Results")
chips = "".join(f"<span class='chip {t['status']}'>{t['step']} · {t['seconds']}s</span>" for t in res.trace)
st.markdown(f"**Workflow:** {' → '.join(res.workflow)}<br>{chips}", unsafe_allow_html=True)
for name, msg in res.errors.items():
    st.error(f"**{name} failed:** {msg}")

tabs = st.tabs(["Overview", "Bug Finder", "Style Reviewer", "Fixed Code", "Test Results", "RAG Sources", "Final Report"])

with tabs[0]:
    a, b, c, d = st.columns(4)
    a.metric("Detected intent", LABELS[res.intent])
    b.metric("Issues found", s["bugs"] + s["style_findings"])
    c.metric("Tests passed", f"{s['tests_passed']}/{s['tests_total']}" if s["tests_total"] else "n/a")
    d.metric("Quality score", f"{s['quality_score']}/10" if s["quality_score"] else "n/a")
    st.markdown(f"<div class='card'><b>Assessment:</b> {s['verdict']}<br><b>Routing:</b> {res.intent_method} - {res.intent_reason}</div>", unsafe_allow_html=True)
    if res.explanation:
        st.markdown(res.explanation)

with tabs[1]:
    if not res.bug_report:
        st.info("Bug Finder did not run in this workflow." if "Bug Finder" not in res.workflow else "No bug report available.")
    else:
        st.write(res.bug_report.summary)
        for bug in res.bug_report.bugs:
            with st.expander(f"{bug.title}  ·  {bug.severity}", expanded=True):
                st.markdown(f"<span class='sev sev-{bug.severity}'>{bug.severity}</span> &nbsp; `{bug.line_hint}`", unsafe_allow_html=True)
                st.markdown(f"**Why it happens:** {bug.explanation}\n\n**Suggested resolution:** {bug.suggested_fix}")

with tabs[2]:
    r = res.style_report
    if not r:
        st.info("Style review runs in the **Code review** workflow.")
    else:
        st.metric("Code quality", f"{r.quality_score}/10")
        st.write(r.assessment)
        if r.strengths:
            st.markdown("**Strengths**\n" + "\n".join(f"- {x}" for x in r.strengths))
        for f in r.findings:
            st.markdown(f"<div class='card'><span class='chip'>{f.category}</span> {f.finding}<br>💡 {f.suggestion}</div>", unsafe_allow_html=True)

with tabs[3]:
    if not res.fix:
        st.info("The Fixer runs in the **Debugging** workflow.")
    else:
        st.code(res.fix.fixed_code, language=res.language.lower())
        st.download_button("⬇️ Download fixed code", res.fix.fixed_code, f"fixed_code.{EXT[res.language]}")
        st.markdown("**What changed**\n" + "\n".join(f"- {c}" for c in res.fix.changes))
        st.markdown(f"**🔁 Reflection:** {res.fix.reflection}")
        for c in res.fix.remaining_concerns:
            st.warning(c)

with tabs[4]:
    if not res.tests:
        st.info("Tests are produced in the Debugging and Test generation workflows.")
    else:
        st.caption(f"Tests run against the **{res.test_target}**.")
        by_name = {x["name"]: x for x in res.test_results}
        base = {x["name"]: x for x in res.baseline_results}
        rows = []
        for t in res.tests:
            x = by_name.get(t.name, {})
            row = {"Test": t.name, "Type": t.category, "Call": t.call_expression, "Expected": t.expected_expression,
                   "Actual": x.get("actual") or x.get("error", "-"), "Status": STATUS_ICON.get(x.get("status"), "— not run")}
            if base:
                row["Original code"] = STATUS_ICON.get(base.get(t.name, {}).get("status"), "—")
            rows.append(row)
        st.dataframe(rows, use_container_width=True, hide_index=True)
        if res.exec_note:
            st.warning(res.exec_note)
        st.caption("Sandbox: isolated subprocess, timeout, scrubbed environment, blocked dangerous imports. Not a container-grade sandbox.")

with tabs[5]:
    st.markdown("Agentic RAG: each agent's retrieval is a **decision** made by the workflow.")
    for e in res.rag_events:
        icon = "🔎" if e["retrieved"] else "⏭️"
        with st.expander(f"{icon} {e['agent']} — {'retrieved ' + str(len(e['docs'])) + ' docs' if e['retrieved'] else 'retrieval skipped'}", expanded=e["retrieved"]):
            st.caption(f"Decision: {e['reason']}")
            if e["retrieved"]:
                st.caption(f"Query: {e['query'][:200]}")
            for d in e["docs"]:
                st.markdown(f"**{d['source']}** · topic `{d['topic']}` · lang `{d['language']}` · similarity **{d['score']}**")
                st.write(d["content"])
            if e["docs"]:
                st.info("These passages were injected into the agent's prompt as retrieved context.")

with tabs[6]:
    report = generate_report(res)
    st.download_button("⬇️ Download review report (.md)", report, "code_review_report.md", "text/markdown")
    st.markdown(report)
