"""Built-in sample knowledge base (seeded into ChromaDB automatically) + optional files from data/coding_guidelines/."""
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "coding_guidelines"

KB = [
    dict(id="dbg-001", language="general", topic="debugging", type="guideline", source="Debugging Playbook",
         text="Common logic bugs: wrong initial value for min/max (starting max at 0 fails for all-negative input), off-by-one loop bounds, using = instead of ==, wrong comparison direction, and mutating a collection while iterating. Initialise accumulators from the first element or from None, not from an arbitrary constant."),
    dict(id="dbg-002", language="general", topic="debugging", type="guideline", source="Debugging Playbook",
         text="Edge cases to always check: empty input, single element, duplicates, negative numbers, zero, very large values, None/null, and boundary indexes (0 and n-1). Many runtime errors such as IndexError, ZeroDivisionError and NullPointerException come from unhandled empty or null input."),
    dict(id="dbg-003", language="general", topic="debugging", type="guideline", source="Debugging Playbook",
         text="Infinite loops: a while loop whose condition variable is never updated, updated in the wrong direction, or compared with floating point equality will never terminate. Verify that every iteration moves the loop variable toward the exit condition."),
    dict(id="dbg-004", language="python", topic="debugging", type="example", source="Python Debugging Examples",
         text="Example: def find_max(arr): max_num = 0 ... returns 0 for [-5, -2, -9]. Fix: handle empty list (return None) and initialise max_num = arr[0]. Other Python pitfalls: mutable default arguments (def f(x, items=[])), modifying a list while iterating, integer vs float division, and catching bare except."),
    dict(id="dbg-005", language="java", topic="debugging", type="example", source="Java Debugging Examples",
         text="Java pitfalls: comparing Strings with == instead of equals(), NullPointerException from unchecked null references, ArrayIndexOutOfBoundsException from i <= arr.length, integer overflow in int arithmetic, and integer division truncating results. Initialise max with Integer.MIN_VALUE or arr[0]."),
    dict(id="dbg-006", language="c", topic="debugging", type="example", source="C Debugging Examples",
         text="C pitfalls: buffer overflows from unchecked array indexes or strcpy, uninitialised variables, memory leaks (malloc without free), use-after-free, dangling pointers, missing null terminator on strings, and using = in conditions. Always check malloc return values and array bounds."),
    dict(id="sty-001", language="python", topic="style", type="standard", source="PEP 8 Summary",
         text="PEP 8: snake_case for functions and variables, PascalCase for classes, UPPER_CASE for constants, 4 spaces per indent, lines under 79-99 characters, two blank lines between top-level definitions, descriptive names (avoid single letters except loop counters), docstrings for public functions, and type hints for clarity."),
    dict(id="sty-002", language="python", topic="style", type="standard", source="Pythonic Idioms",
         text="Pythonic idioms: use built-ins like max(), min(), sum(), any(), all(); prefer list comprehensions for simple transforms; use enumerate() instead of range(len()); use 'with' for files; avoid shadowing built-ins such as max, list or sum; prefer 'is None' for None checks."),
    dict(id="sty-003", language="java", topic="style", type="standard", source="Java Code Conventions",
         text="Java conventions: camelCase for methods and variables, PascalCase for classes, UPPER_SNAKE_CASE for constants, braces on every block, one top-level class per file, meaningful names, Javadoc for public methods, prefer enhanced for-loops and Optional over returning null, and keep methods short."),
    dict(id="sty-004", language="c", topic="style", type="standard", source="C Best Practices",
         text="C best practices: consistent naming (snake_case), define constants with const or #define in UPPER_CASE, one declaration per line, always use braces for if/for/while, check return values, free every allocation, limit global variables, and comment non-obvious logic."),
    dict(id="sty-005", language="general", topic="style", type="guideline", source="Clean Code Principles",
         text="Clean code: functions should do one thing, names should reveal intent, avoid deep nesting (use early returns), remove duplicated code, avoid magic numbers, keep cyclomatic complexity low, and write comments that explain why rather than what."),
    dict(id="tst-001", language="general", topic="testing", type="guideline", source="Testing Guidelines",
         text="Good unit tests cover: normal inputs, edge cases (empty, single element, negatives, zero), boundary values (minimum/maximum, first/last index), and invalid input behaviour. Each test should be independent, deterministic and assert one clear expectation. Expected values come from the specification, not from the current implementation."),
    dict(id="tst-002", language="python", topic="testing", type="guideline", source="Python Testing Tips",
         text="Python testing: pytest or unittest, name tests after behaviour (test_returns_none_for_empty_list), use parametrization for many input/output pairs, compare floats with tolerance (math.isclose), and test exceptions explicitly with pytest.raises."),
    dict(id="exp-001", language="general", topic="explanation", type="guideline", source="Complexity Cheatsheet",
         text="Complexity basics: a single loop over n items is O(n); nested loops are O(n^2); binary search is O(log n); sorting is typically O(n log n); finding a max in an unsorted list needs O(n) time and O(1) extra space."),
    dict(id="sec-001", language="general", topic="debugging", type="guideline", source="Defensive Programming",
         text="Defensive programming: validate inputs at function boundaries, fail fast with clear error messages, prefer explicit return values for empty results (None/Optional), avoid swallowing exceptions, and never trust user input."),
]


def load_extra_documents():
    """Any .md/.txt file dropped into data/coding_guidelines/ is added to the vector DB automatically."""
    docs = []
    if DATA_DIR.exists():
        for p in sorted(DATA_DIR.glob("*")):
            if p.suffix.lower() in (".md", ".txt"):
                text = p.read_text(encoding="utf-8", errors="ignore").strip()
                if text:
                    docs.append(dict(id=f"file-{p.stem}", language="general", topic="guideline",
                                     type="file", source=p.name, text=text[:3000]))
    return docs


def all_documents():
    return KB + load_extra_documents()
