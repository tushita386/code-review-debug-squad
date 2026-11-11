"""Pydantic schemas = structured output contracts for every agent."""
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator


class Bug(BaseModel):
    title: str = Field(description="Short name of the bug")
    severity: Literal["Critical", "High", "Medium", "Low"]
    line_hint: str = Field(default="", description="Line number or code fragment")
    explanation: str = Field(description="Why the issue occurs")
    suggested_fix: str = Field(description="How to resolve it")

    @field_validator("severity", mode="before")
    @classmethod
    def _sev(cls, v):
        return v.strip().capitalize() if isinstance(v, str) else v


class BugReport(BaseModel):
    summary: str
    bugs: List[Bug] = Field(default_factory=list)


class StyleFinding(BaseModel):
    category: str = Field(description="naming | readability | complexity | formatting | best-practice")
    finding: str
    suggestion: str


class StyleReport(BaseModel):
    quality_score: int = Field(description="Overall quality from 1 (poor) to 10 (excellent)")
    assessment: str
    strengths: List[str] = Field(default_factory=list)
    findings: List[StyleFinding] = Field(default_factory=list)

    @field_validator("quality_score", mode="before")
    @classmethod
    def _clamp(cls, v):
        return max(1, min(10, int(float(v))))


class FixDraft(BaseModel):
    fixed_code: str
    changes: List[str] = Field(default_factory=list)


class FixResult(BaseModel):
    fixed_code: str
    changes: List[str] = Field(default_factory=list)
    reflection: str = Field(description="Summary of the self-review of the draft")
    remaining_concerns: List[str] = Field(default_factory=list)


class TestCase(BaseModel):
    __test__ = False  # keep pytest from collecting this
    name: str
    category: Literal["normal", "edge", "boundary"]
    call_expression: str = Field(description="Expression that calls the function under test")
    expected_expression: str = Field(description="Literal expression of the expected result")
    description: str = ""

    @field_validator("category", mode="before")
    @classmethod
    def _cat(cls, v):
        v = str(v).strip().lower()
        return v if v in ("normal", "edge", "boundary") else "normal"


class TestSuite(BaseModel):
    __test__ = False
    function_name: str = ""
    tests: List[TestCase] = Field(default_factory=list)
