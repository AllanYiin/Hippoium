import pytest

from hippoium.adapters.openai import OpenAIAdapter
from hippoium.adapters.retry import RetryConfig
from hippoium.errors import BadRequestError, TimeoutError


class FakeRateLimitError(Exception):
    def __init__(self, message: str, status_code: int = 429, request_id: str = "req-429") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


class FakeTimeoutException(Exception):
    pass


class FakeBadRequest(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class FlakyChatCompletion:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise FakeRateLimitError("rate limited")
        return {"id": "req-200", "choices": [{"message": {"content": "ok"}}]}


class TimeoutChatCompletion:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        raise FakeTimeoutException("timeout")


class BadRequestChatCompletion:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        raise FakeBadRequest("bad request")


class FakeEmbedding:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return {"data": [{"embedding": [1.0]}]}


class FakeOpenAI:
    def __init__(self, chat_completion) -> None:
        self.api_key = "unset"
        self.ChatCompletion = chat_completion
        self.Embedding = FakeEmbedding()


def test_retry_on_rate_limit_then_success(monkeypatch):
    fake = FakeOpenAI(FlakyChatCompletion())
    monkeypatch.setattr("hippoium.adapters.openai.openai", fake)
    monkeypatch.setattr("hippoium.adapters.retry.time.sleep", lambda *_: None)

    adapter = OpenAIAdapter(api_key="key-123", retry_config=RetryConfig(max_attempts=2, base_delay=0))
    assert adapter.complete("hi") == "ok"
    assert fake.ChatCompletion.calls == 2


def test_timeout_retries_then_raises(monkeypatch):
    fake = FakeOpenAI(TimeoutChatCompletion())
    monkeypatch.setattr("hippoium.adapters.openai.openai", fake)
    monkeypatch.setattr("hippoium.adapters.retry.time.sleep", lambda *_: None)

    adapter = OpenAIAdapter(api_key="key-123", retry_config=RetryConfig(max_attempts=2, base_delay=0))
    with pytest.raises(TimeoutError):
        adapter.complete("hi")
    assert fake.ChatCompletion.calls == 2


def test_bad_request_no_retry(monkeypatch):
    fake = FakeOpenAI(BadRequestChatCompletion())
    monkeypatch.setattr("hippoium.adapters.openai.openai", fake)
    monkeypatch.setattr("hippoium.adapters.retry.time.sleep", lambda *_: None)

    adapter = OpenAIAdapter(api_key="key-123", retry_config=RetryConfig(max_attempts=3, base_delay=0))
    with pytest.raises(BadRequestError):
        adapter.complete("hi")
    assert fake.ChatCompletion.calls == 1
