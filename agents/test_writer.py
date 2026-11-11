"""Agent 4 - Test Writer: generates tests (LCEL) and executes them in the restricted subprocess (Python only)."""
from core.chains import build_chain, run_chain
from core.prompts import TEST_PROMPT
from core.schemas import TestSuite
from tools.code_executor import run_python_tests


def run(language: str, code: str, request: str, context: str) -> TestSuite:
    chain = build_chain(TEST_PROMPT, TestSuite)
    return run_chain(chain, {"language": language.lower(), "code": code,
                             "request": request or "Generate tests.", "context": context})


def execute(tests, code: str):
    return run_python_tests(code, tests)
