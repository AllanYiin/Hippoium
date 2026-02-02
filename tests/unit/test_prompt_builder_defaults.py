from hippoium.core.builder.prompt_builder import PromptBuilder


def test_prompt_builder_default_context_is_none():
    defaults = PromptBuilder.build.__defaults__
    assert defaults is not None
    # defaults: template_id, context, user_query, negative_examples, tools, token_budget
    assert defaults[1] is None
    assert defaults[-1] is None
