from __future__ import annotations

import logging
import os
from typing import Iterable, Sequence

from hippoium.core.builder.prompt_builder import PromptBuilder
from hippoium.engine import DefaultContextEngine
from hippoium.ports.domain import Message
from hippoium.ports.protocols import EmbeddingClient, LLMClient


def setup_logger(name: str) -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(os.path.join("logs", f"{name}.log"), encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


class MockLLMClient(LLMClient):
    def complete(self, messages: Sequence[Message] | Sequence[dict], **opts: object) -> str:
        del opts
        last = messages[-1]["content"] if messages else ""
        return f"（Mock 回覆）你剛剛問：{last}。提醒：這是 Mock 模式。"


class MockEmbeddingClient(EmbeddingClient):
    def embed(self, texts: Iterable[str], **opts: object) -> list[list[float]]:
        del opts
        return [[float(len(text)), 0.0, 0.0] for text in texts]


def main() -> None:
    logger = setup_logger("minimal")
    try:
        engine = DefaultContextEngine()
        engine.write_turn("user", "你好，請簡短介紹 Hippoium")
        engine.write_turn("assistant", "這是範例回覆，用於建立上下文。")
        context = engine.get_context_for_scope("task")

        messages = PromptBuilder().build(
            context=context,
            user_query="請用一句話說明它的用途。",
        )

        llm = MockLLMClient()
        embeddings = MockEmbeddingClient()

        reply = llm.complete(messages)
        vector = embeddings.embed([messages[-1]["content"]])[0]

        print("Mock LLM 回覆：", reply)
        print("Mock 向量：", vector)
        print("提醒：此範例使用 Mock 客戶端，未呼叫任何真實模型。")
    except Exception:
        logger.exception("minimal example failed")
        print("執行失敗，請查看 logs/minimal.log 了解細節。")


if __name__ == "__main__":
    main()
