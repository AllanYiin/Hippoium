"""OpenAI + Hippoium context comparison playground (Streamlit)."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

import pandas as pd
import streamlit as st
from openai import OpenAI

from hippoium.tools.context_lab import (
    build_compression_snapshot,
    build_context_views,
    estimate_tokens,
)

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("context_lab")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "context_lab.log"),
        maxBytes=1_048_576,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(handler)


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "system",
                "content": "你是一位專業且友善的助理，請以繁體中文回覆。",
            }
        ]
    if "history" not in st.session_state:
        st.session_state.history = []


def render_chat() -> None:
    for message in st.session_state.messages:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def stream_openai_response(client: OpenAI, model: str) -> str:
    response_text = ""
    stream = client.chat.completions.create(
        model=model,
        messages=st.session_state.messages,
        temperature=0.2,
        stream=True,
    )
    with st.chat_message("assistant"):
        placeholder = st.empty()
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else ""
            if delta:
                response_text += delta
                placeholder.markdown(response_text)
    return response_text


def main() -> None:
    st.set_page_config(page_title="Hippoium Context Lab", layout="wide")
    st.title("Hippoium Context 測試工具")
    st.caption(
        "左側對話、中間原始 Context、右側 Hippoium Context，"
        "並追蹤壓縮比與費用壓縮比。"
    )

    init_state()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("找不到 OPENAI_API_KEY，請先在環境變數設定。")
        return

    cache_hit_ratio = st.sidebar.slider("Prompt Caching 命中率", 0.0, 1.0, 0.5, 0.05)
    model = st.sidebar.selectbox("OpenAI 模型", ["gpt-4o-mini"])

    col1, col2, col3 = st.columns([1.1, 1.0, 1.0])

    with col1:
        st.subheader("對話")
        render_chat()
        prompt = st.chat_input("請輸入問題")

    with col2:
        st.subheader("Assistant 原始 Context")
        raw_context, hippo_context = build_context_views(st.session_state.messages, "")
        st.text_area("Raw Context", raw_context, height=420)

    with col3:
        st.subheader("Hippoium 處理後 Context")
        st.text_area("Hippo Context", hippo_context, height=420)

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        try:
            client = OpenAI(api_key=api_key)
            answer = stream_openai_response(client, model)
            st.session_state.messages.append({"role": "assistant", "content": answer})

            raw_context, hippo_context = build_context_views(
                st.session_state.messages,
                prompt,
            )
            output_tokens = estimate_tokens(answer)
            snapshot = build_compression_snapshot(
                turn=len(st.session_state.history) + 1,
                raw_context=raw_context,
                hippo_context=hippo_context,
                output_tokens=output_tokens,
                cache_hit_ratio=cache_hit_ratio,
                model=model,
            )
            st.session_state.history.append(snapshot)

        except Exception:  # noqa: BLE001
            logger.exception("OpenAI 呼叫失敗")
            st.error("OpenAI 呼叫失敗，請稍後再試或檢查 API 設定。")

    if st.session_state.history:
        st.divider()
        st.subheader("壓縮歷史")
        frame = pd.DataFrame([s.__dict__ for s in st.session_state.history])
        st.dataframe(
            frame.assign(
                compression_ratio=lambda df: (df["compression_ratio"] * 100).round(2),
                cost_compression_ratio=lambda df: (
                    df["cost_compression_ratio"] * 100
                ).round(2),
            ),
            use_container_width=True,
        )
        st.line_chart(
            frame.set_index("turn")[["compression_ratio", "cost_compression_ratio"]],
            use_container_width=True,
        )


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        logger.exception("Context Lab 啟動失敗")
        raise
