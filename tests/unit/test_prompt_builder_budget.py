from hippoium.core.builder.prompt_builder import PromptBuilder
from hippoium.ports.domain import MemoryItem


def test_token_budget_trims_context_first():
    builder = PromptBuilder()
    template = "System: Context\n{context}\nUser: {user_query}"
    builder.registry.register_template("budget_context", template)
    context = [
        MemoryItem(content="alpha beta gamma", metadata={"role": "user"}),
        MemoryItem(content="delta epsilon zeta", metadata={"role": "assistant"}),
        MemoryItem(content="eta theta iota", metadata={"role": "assistant"}),
    ]
    payload = builder.build_payload(
        template_id="budget_context",
        context=context,
        user_query="hello",
        token_budget=40,
    )
    assert payload.trimmed["context"] >= 1
    system_text = "\n".join(m["content"] for m in payload.messages if m["role"] == "system")
    assert "alpha beta gamma" not in system_text
    assert "eta theta iota" in system_text
