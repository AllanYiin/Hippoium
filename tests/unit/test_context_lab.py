import unittest

from hippoium.tools.context_lab import (
    build_compression_snapshot,
    build_context_views,
    estimate_turn_cost,
)


class TestContextLab(unittest.TestCase):
    def test_build_context_views_returns_both_views(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "哈囉"},
            {"role": "assistant", "content": "您好"},
        ]

        raw_context, hippo_context = build_context_views(messages, "下一題")

        self.assertIn("[user]", raw_context)
        self.assertIn("哈囉", hippo_context)
        self.assertIn("下一題", hippo_context)

    def test_estimate_turn_cost_with_prompt_cache(self):
        normal = estimate_turn_cost(
            input_tokens=1000,
            output_tokens=200,
            cached_input_tokens=0,
        )
        cached = estimate_turn_cost(
            input_tokens=1000,
            output_tokens=200,
            cached_input_tokens=800,
        )

        self.assertLess(cached, normal)

    def test_compression_snapshot_ratios(self):
        snapshot = build_compression_snapshot(
            turn=1,
            raw_context="a" * 2000,
            hippo_context="a" * 800,
            output_tokens=100,
            cache_hit_ratio=0.5,
        )

        self.assertLess(snapshot.compression_ratio, 1.0)
        self.assertLess(snapshot.cost_compression_ratio, 1.0)


if __name__ == "__main__":
    unittest.main()
