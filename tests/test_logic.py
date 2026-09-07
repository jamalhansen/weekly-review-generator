from pydantic import BaseModel

from weekly_review.logic import process_llm_response


class _FakeLLMResponse(BaseModel):
    headline: str = "Test week"


class TestProcessLlmResponse:
    def test_accepts_plain_dict(self):
        review = process_llm_response({"headline": "Dict week"}, "2026-01-05", 100)
        assert review.week_of == "2026-01-05"
        assert review.word_count_input == 100
        assert review.headline == "Dict week"

    def test_accepts_pydantic_model_via_model_dump(self):
        review = process_llm_response(_FakeLLMResponse(), "2026-01-05", 100)
        assert review.headline == "Test week"
        assert review.week_of == "2026-01-05"
