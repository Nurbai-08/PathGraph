from app.schemas.concept import ConceptExtractionOutput
from app.services.ai.providers import GEMINI_UNSUPPORTED_SCHEMA_KEYS, gemini_response_schema


def test_gemini_schema_removes_unsupported_validation_keywords() -> None:
    schema = gemini_response_schema(ConceptExtractionOutput.model_json_schema())

    def walk(value: object) -> None:
        if isinstance(value, dict):
            assert not GEMINI_UNSUPPORTED_SCHEMA_KEYS.intersection(value)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(schema)
    assert isinstance(schema, dict)
    assert "$defs" in schema
    assert schema["type"] == "object"
