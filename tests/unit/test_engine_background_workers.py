import time
import unittest

from hippoium.engine import DefaultContextEngine


class TestEngineBackgroundWorkers(unittest.TestCase):
    def test_write_turn_is_non_blocking_with_background_memory_worker(self):
        engine = DefaultContextEngine(enable_background_workers=True, housekeeping_interval_seconds=1)
        try:
            engine.write_turn("user", "hello", {"session_id": "s1"})
            deadline = time.time() + 1.0
            history = []
            while time.time() < deadline:
                history = engine.s_cache.get("s1") or []
                if history:
                    break
                time.sleep(0.01)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].content, "hello")
        finally:
            engine.close()

    def test_compression_runs_in_background_and_returns_cached_result(self):
        engine = DefaultContextEngine(enable_background_workers=True, housekeeping_interval_seconds=1)
        try:
            for idx in range(60):
                engine.write_turn("user", f"訊息-{idx}", {"session_id": "s2"})

            deadline = time.time() + 1.0
            while time.time() < deadline:
                history = engine.s_cache.get("s2") or []
                if len(history) == 60:
                    break
                time.sleep(0.01)

            first = engine.get_context_for_scope("task", key="s2")
            self.assertEqual(len(first), 50)
            self.assertTrue(all("compressed" not in item.metadata for item in first))

            deadline = time.time() + 1.0
            second = first
            while time.time() < deadline:
                second = engine.get_context_for_scope("task", key="s2")
                if second and all(item.metadata.get("compressed") for item in second):
                    break
                time.sleep(0.01)

            self.assertEqual(len(second), 50)
            self.assertTrue(all(item.metadata.get("compressed") for item in second))
        finally:
            engine.close()


if __name__ == "__main__":
    unittest.main()
