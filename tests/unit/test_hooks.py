import logging

from hippoium.core.hooks import HookRegistry


def test_register_decorator_and_notify_logs_error(caplog):
    registry = HookRegistry()
    calls = []

    @registry.register("demo")
    def good_hook():
        calls.append("good")

    @registry.register("demo")
    def bad_hook():
        raise ValueError("boom")

    with caplog.at_level(logging.ERROR):
        registry.notify("demo")

    assert calls == ["good"]
    assert any(
        "Hook callback failed for event demo: bad_hook" in record.getMessage()
        for record in caplog.records
    )
