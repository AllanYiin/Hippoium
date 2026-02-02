from __future__ import annotations

import logging
import os
from typing import Sequence

from hippoium.core.builder.prompt_builder import PromptBuilder
from hippoium.engine import DefaultContextEngine
from hippoium.ports.domain import Message
from hippoium.ports.protocols import LLMClient


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


class StreamingOpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def complete(self, messages: Sequence[Message] | Sequence[dict], **opts: object) -> str:
        del opts
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        stream = client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )
        collected: list[str] = []
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                print(delta, end="", flush=True)
                collected.append(delta)
        print()
        return "".join(collected)


def main() -> None:
    logger = setup_logger("openai_live")
    try:
        if os.getenv("CI"):
            print("偵測到 CI 環境，預設不執行 openai_live 範例。")
            return

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("缺少 OPENAI_API_KEY，請先設定環境變數後再執行。")
            return

        engine = DefaultContextEngine()
        engine.write_turn("user", "請用繁體中文簡短介紹 Hippoium")
        context = engine.get_context_for_scope("task")

        messages = PromptBuilder().build(
            context=context,
            user_query="請用一句話說明它適合的使用情境。",
        )

        client = StreamingOpenAIClient(api_key=api_key, model="gpt-3.5-turbo")
        print("=== Streaming 回覆開始 ===")
        client.complete(messages)
        print("=== Streaming 回覆結束 ===")
    except Exception:
        logger.exception("openai_live example failed")
        print("執行失敗，請查看 logs/openai_live.log 了解細節。")


if __name__ == "__main__":
    main()
