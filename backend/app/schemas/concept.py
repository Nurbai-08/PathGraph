from pydantic import BaseModel, Field


class ExtractedConcept(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    type: str = Field(default="concept", min_length=1, max_length=80)
    importance: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    aliases: list[str] = Field(default_factory=list, max_length=20)


class ExtractedRelation(BaseModel):
    source_name: str = Field(min_length=1, max_length=200)
    target_name: str = Field(min_length=1, max_length=200)
    relation_type: str = Field(min_length=1, max_length=40)
    confidence: float = Field(ge=0, le=1)


class ConceptExtractionOutput(BaseModel):
    concepts: list[ExtractedConcept] = Field(default_factory=list, max_length=30)
    relationships: list[ExtractedRelation] = Field(default_factory=list, max_length=60)


class MergeDecision(BaseModel):
    same_concept: bool
