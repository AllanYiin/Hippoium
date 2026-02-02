import pytest

from hippoium.adapters.openai import OpenAIAdapter


class FakeChatCompletion:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return {"choices": [{"message": {"content": "ok"}}]}


class FakeEmbedding:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return {"data": [{"embedding": [1.0, 2.0, 3.0]}]}


class FakeOpenAI:
    def __init__(self):
        self.api_key = "unset"
        self.ChatCompletion = FakeChatCompletion()
        self.Embedding = FakeEmbedding()


def test_openai_adapter_uses_instance_key(monkeypatch):
    fake = FakeOpenAI()
    monkeypatch.setattr("hippoium.adapters.openai.openai", fake)

    adapter = OpenAIAdapter(api_key="key-123")
    assert fake.api_key == "unset"

    adapter.complete("hi")
    assert fake.ChatCompletion.calls[-1]["api_key"] == "key-123"

    adapter.embeddings("text")
    assert fake.Embedding.calls[-1]["api_key"] == "key-123"


def test_openai_adapter_sequence_validation(monkeypatch):
    fake = FakeOpenAI()
    monkeypatch.setattr("hippoium.adapters.openai.openai", fake)

    adapter = OpenAIAdapter(api_key="key-456")
    prompt = (
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    )
    assert adapter.complete(prompt) == "ok"

    with pytest.raises(ValueError):
        adapter.complete(["not-a-dict"])

    with pytest.raises(ValueError):
        adapter.complete([{"role": "user"}])
