"""LCEL chains: prompt | llm | text-normaliser | output parser  (pipe operator)."""
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.runnables import RunnableLambda

from .llm import get_llm
from .prompts import EXPLAIN_PROMPT, INTENT_PROMPT


def _msg_text(msg) -> str:
    content = getattr(msg, "content", msg)
    if isinstance(content, list):
        content = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content).strip()


def _json_only(msg) -> str:
    """Strip code fences / chatter so the Pydantic parser sees pure JSON."""
    text = _msg_text(msg)
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else text


def build_chain(prompt, schema):
    parser = PydanticOutputParser(pydantic_object=schema)
    return (
        prompt.partial(format_instructions=parser.get_format_instructions())
        | get_llm()
        | RunnableLambda(_json_only)
        | parser
    )


def run_chain(chain, inputs: dict, retries: int = 1):
    """Invoke a chain; retry once if the model returns malformed structured output."""
    for attempt in range(retries + 1):
        try:
            return chain.invoke(inputs)
        except OutputParserException:
            if attempt == retries:
                raise ValueError("The model returned malformed output twice; please try again.")


def explain_chain():
    return EXPLAIN_PROMPT | get_llm(0.3) | StrOutputParser()


def intent_chain():
    return INTENT_PROMPT | get_llm(0.0) | RunnableLambda(_msg_text)


def explain_code(language: str, code: str, request: str, context: str) -> str:
    return explain_chain().invoke(
        {"language": language.lower(), "code": code, "request": request or "Explain this code.", "context": context}
    )
