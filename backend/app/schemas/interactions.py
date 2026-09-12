from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ExplainRequest(BaseModel):
    mode: Literal["standard", "simpler"] = "standard"


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)


class CompareRequest(BaseModel):
    concept_a_id: UUID
    concept_b_id: UUID


class GroundedGeneration(BaseModel):
    source_backed_answer: str = Field(default="", max_length=12000)
    additional_explanation: str = Field(default="", max_length=12000)
    citation_indices: list[int] = Field(default_factory=list, max_length=20)


class WhyGeneration(GroundedGeneration):
    why_it_matters: str = Field(default="", max_length=6000)


class CompareGeneration(BaseModel):
    similarities: list[str] = Field(default_factory=list, max_length=20)
    differences: list[str] = Field(default_factory=list, max_length=20)
    when_to_use_a: list[str] = Field(default_factory=list, max_length=20)
    when_to_use_b: list[str] = Field(default_factory=list, max_length=20)
    examples: list[str] = Field(default_factory=list, max_length=20)
    citation_indices: list[int] = Field(default_factory=list, max_length=20)


class CitationRead(BaseModel):
    index: int
    source_id: UUID
    source_title: str
    chunk_id: UUID
    heading_path: str
    excerpt: str


class GroundedAnswerRead(BaseModel):
    source_backed_answer: str
    additional_explanation: str
    citations: list[CitationRead]


class WhyAnswerRead(GroundedAnswerRead):
    why_it_matters: str
    path: list[str]


class CompareAnswerRead(BaseModel):
    concept_a: str
    concept_b: str
    similarities: list[str]
    differences: list[str]
    when_to_use_a: list[str]
    when_to_use_b: list[str]
    examples: list[str]
    citations: list[CitationRead]
