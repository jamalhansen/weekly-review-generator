import json
from unittest.mock import MagicMock, patch

import pytest

from local_first_common.providers.base import BaseProvider
from local_first_common.providers.ollama import OllamaProvider
from local_first_common.providers.anthropic import AnthropicProvider
from local_first_common.providers.groq import GroqProvider
from local_first_common.providers.deepseek import DeepSeekProvider
from local_first_common.providers import PROVIDERS
from schema import WeekReview


SAMPLE_REVIEW_JSON = json.dumps({
    "week_of": "2026-02-23",
    "headline": "A solid week",
    "highlights": [{"category": "Work", "summary": "Got things done", "items": []}],
    "links_saved": [],
    "open_threads": [],
    "word_count_input": 100,
})


class TestProvidersDict:
    def test_all_providers_registered(self):
        assert set(PROVIDERS.keys()) == {"ollama", "anthropic", "gemini", "groq", "deepseek"}

    def test_provider_instantiation_pattern(self):
        # Each cloud provider requires an API key — just verify the class is callable
        assert callable(PROVIDERS["ollama"])


class TestBaseProvider:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseProvider()

    def test_get_example_json_simple_model(self):
        class ConcreteProvider(BaseProvider):
            default_model = "test"
            known_models = []
            models_url = "http://example.com"

            def complete(self, system, user, response_model=None):
                return ""

        provider = ConcreteProvider()
        result = provider._get_example_json(WeekReview)
        parsed = json.loads(result)
        assert "week_of" in parsed
        assert "highlights" in parsed


class TestOllamaProvider:
    def test_default_model(self):
        p = OllamaProvider()
        assert p.model == "phi4-mini"

    def test_custom_model(self):
        p = OllamaProvider(model="llama3")
        assert p.model == "llama3"

    def test_complete_returns_parsed_dict(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": SAMPLE_REVIEW_JSON}
        mock_response.raise_for_status = MagicMock()

        with patch("local_first_common.providers.ollama.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            p = OllamaProvider()
            result = p.complete("system", "user", response_model=WeekReview)

        assert isinstance(result, dict)
        assert result["headline"] == "A solid week"

    def test_model_not_found_raises_runtime_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("local_first_common.providers.ollama.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            p = OllamaProvider(model="nonexistent-model")
            # Patch _get_installed_models to avoid real network call
            p._get_installed_models = MagicMock(return_value=[])

            with pytest.raises(RuntimeError, match="not found"):
                p.complete("sys", "usr")


class TestAnthropicProvider:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            AnthropicProvider(api_key=None)

    def test_default_model(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        p = AnthropicProvider()
        assert p.model == AnthropicProvider.default_model

    def test_complete_returns_parsed_dict(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_content = MagicMock()
        mock_content.text = SAMPLE_REVIEW_JSON
        mock_message = MagicMock()
        mock_message.content = [mock_content]

        # The installed local_first_common uses a lazy `_Anthropic` alias
        with patch("local_first_common.providers.anthropic._Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_message
            mock_anthropic.return_value = mock_client

            p = AnthropicProvider()
            result = p.complete("system", "user", response_model=WeekReview)

        assert isinstance(result, dict)
        assert result["headline"] == "A solid week"


class TestGroqProvider:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            GroqProvider(api_key=None)

    def test_complete_returns_parsed_dict(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": SAMPLE_REVIEW_JSON}}]
        }

        with patch("local_first_common.providers.groq.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            p = GroqProvider()
            result = p.complete("system", "user", response_model=WeekReview)

        assert isinstance(result, dict)
        assert result["headline"] == "A solid week"


class TestDeepSeekProvider:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
            DeepSeekProvider(api_key=None)

    def test_default_model(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        p = DeepSeekProvider()
        assert p.model == "deepseek-chat"
