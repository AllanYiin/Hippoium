from hippoium.core.routing.cost_router import CostRouter
from hippoium.core.routing.fallback_manager import FallbackManager


class FakeClient:
    def __init__(self, response: str, fail: bool = False) -> None:
        self.response = response
        self.fail = fail
        self.calls = []

    def complete(self, messages, **opts):
        self.calls.append(messages)
        if self.fail:
            raise RuntimeError("boom")
        return self.response


def test_cost_router_selects_provider():
    alpha = FakeClient("alpha")
    beta = FakeClient("beta")
    router = CostRouter({"alpha": alpha, "beta": beta})

    choice = router.select("prompt")

    assert choice in (alpha, beta)


def test_fallback_manager_uses_secondary_on_failure():
    primary = FakeClient("primary", fail=True)
    secondary = FakeClient("secondary")
    manager = FallbackManager(primary=primary, secondary=secondary)

    result = manager.execute("hello")

    assert result == "secondary"
    assert primary.calls
    assert secondary.calls
