import pytest
from pydantic import BaseModel

from app.services.llm.gemini import GeminiLLMService


class DummySchema(BaseModel):
    summary: str
    value: int = 0


class FakeResponse:
    def __init__(self, parsed=None, text=None):
        self.parsed = parsed
        self.text = text


class FakeAPIError(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__(f"fake api error {status}")


class FakeErrorsModule:
    APIError = FakeAPIError


class FakeHttpOptions:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeHttpRetryOptions:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeGenerateContentConfig:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeTypesModule:
    HttpOptions = FakeHttpOptions
    HttpRetryOptions = FakeHttpRetryOptions
    GenerateContentConfig = FakeGenerateContentConfig


def _configured_service(monkeypatch) -> GeminiLLMService:
    service = GeminiLLMService()
    monkeypatch.setattr(service.settings, "gemini_api_key", "fake-key-for-tests")
    return service


def _fake_sdk_returning(outcome):
    class FakeModels:
        def generate_content(self, **kwargs):
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    class FakeClient:
        def __init__(self, **kwargs):
            self.init_kwargs = kwargs
            self.models = FakeModels()

    class FakeGenaiModule:
        Client = FakeClient

    return FakeGenaiModule(), FakeTypesModule(), FakeErrorsModule()


def test_is_configured_false_without_key(monkeypatch):
    service = GeminiLLMService()
    monkeypatch.setattr(service.settings, "gemini_api_key", None)
    assert service.is_configured() is False


def test_generate_raises_when_not_configured(monkeypatch):
    service = GeminiLLMService()
    monkeypatch.setattr(service.settings, "gemini_api_key", None)
    with pytest.raises(RuntimeError, match="not configured"):
        service.generate_viewing_plan(prompt="test")


def test_parse_response_uses_pre_parsed_schema_instance(monkeypatch):
    service = _configured_service(monkeypatch)
    parsed = DummySchema(summary="ok", value=1)
    result = service._parse_response(FakeResponse(parsed=parsed), DummySchema, model="test-model")
    assert result is parsed


def test_parse_response_validates_pre_parsed_dict(monkeypatch):
    service = _configured_service(monkeypatch)
    response = FakeResponse(parsed={"summary": "ok", "value": 2})
    result = service._parse_response(response, DummySchema, model="test-model")
    assert result.value == 2


def test_parse_response_rejects_pre_parsed_dict_failing_schema(monkeypatch):
    service = _configured_service(monkeypatch)
    response = FakeResponse(parsed={"value": "not-an-int"})
    with pytest.raises(RuntimeError, match="did not match the expected schema"):
        service._parse_response(response, DummySchema, model="test-model")


def test_parse_response_parses_valid_json_text(monkeypatch):
    service = _configured_service(monkeypatch)
    response = FakeResponse(text='{"summary": "from text", "value": 5}')
    result = service._parse_response(response, DummySchema, model="test-model")
    assert result.summary == "from text"
    assert result.value == 5


def test_parse_response_rejects_malformed_json_text(monkeypatch):
    service = _configured_service(monkeypatch)
    response = FakeResponse(text="not json at all {{{")
    with pytest.raises(RuntimeError, match="not valid JSON"):
        service._parse_response(response, DummySchema, model="test-model")


def test_parse_response_rejects_valid_json_failing_schema(monkeypatch):
    service = _configured_service(monkeypatch)
    response = FakeResponse(text='{"unexpected_field": true}')
    with pytest.raises(RuntimeError, match="did not match the expected schema"):
        service._parse_response(response, DummySchema, model="test-model")


def test_parse_response_rejects_empty_response(monkeypatch):
    service = _configured_service(monkeypatch)
    response = FakeResponse(parsed=None, text=None)
    with pytest.raises(RuntimeError, match="empty"):
        service._parse_response(response, DummySchema, model="test-model")


def test_generate_raises_runtime_error_on_rate_limit(monkeypatch):
    service = _configured_service(monkeypatch)
    monkeypatch.setattr(service, "_load_sdk", lambda: _fake_sdk_returning(FakeAPIError(429)))

    with pytest.raises(RuntimeError, match="rate limit"):
        service._generate(model="test-model", prompt="test", response_schema=DummySchema)


def test_generate_raises_runtime_error_on_server_error(monkeypatch):
    service = _configured_service(monkeypatch)
    monkeypatch.setattr(service, "_load_sdk", lambda: _fake_sdk_returning(FakeAPIError(503)))

    with pytest.raises(RuntimeError, match="status=503"):
        service._generate(model="test-model", prompt="test", response_schema=DummySchema)


def test_generate_returns_parsed_schema_on_success(monkeypatch):
    service = _configured_service(monkeypatch)
    parsed = DummySchema(summary="ok", value=7)
    monkeypatch.setattr(service, "_load_sdk", lambda: _fake_sdk_returning(FakeResponse(parsed=parsed)))

    result = service._generate(model="test-model", prompt="test", response_schema=DummySchema)
    assert result is parsed
