from pathlib import Path

# －－－列出所有需要的程式檔路徑－－－
# －－－列出所有需要的程式檔路徑－－－
PROJECT_FILES = [
    # ──專案根目錄──
    "README.md",
    "pyproject.toml",

    # ──主套件目錄──
    "hippoium/__init__.py",

    # ── ports ─────────────────────────────
    "hippoium/ports/__init__.py",
    "hippoium/ports/port_types.py",
    "hippoium/ports/protocols.py",
    "hippoium/ports/events.py",
    "hippoium/ports/exceptions.py",
    "hippoium/ports/schemas.py",

    # ── core ─────────────────────────────
    "hippoium/core/__init__.py",

    # cer
    "hippoium/core/cer/__init__.py",
    "hippoium/core/cer/runtime.py",
    "hippoium/core/cer/cache.py",
    "hippoium/core/cer/compressor.py",
    "hippoium/core/cer/telemetry.py",

    # builder
    "hippoium/core/builder/__init__.py",
    "hippoium/core/builder/prompt_builder.py",
    "hippoium/core/builder/template_engine.py",
    "hippoium/core/builder/slot_injector.py",
    "hippoium/core/builder/validator.py",

    # retriever
    "hippoium/core/retriever/__init__.py",
    "hippoium/core/retriever/hybrid_retriever.py",
    "hippoium/core/retriever/scorer.py",
    "hippoium/core/retriever/deduper.py",
    "hippoium/core/retriever/reranker.py",

    # memory
    "hippoium/core/memory/__init__.py",
    "hippoium/core/memory/stores.py",
    "hippoium/core/memory/lifecycle.py",
    "hippoium/core/memory/compression.py",
    "hippoium/core/memory/sampler.py",

    # negative
    "hippoium/core/negative/__init__.py",
    "hippoium/core/negative/negative_engine.py",
    "hippoium/core/negative/pattern_detector.py",
    "hippoium/core/negative/semantic_patch.py",
    "hippoium/core/negative/auto_labeler.py",

    # patch
    "hippoium/core/patch/__init__.py",
    "hippoium/core/patch/patch_manager.py",
    "hippoium/core/patch/ast_analyzer.py",
    "hippoium/core/patch/diff_generator.py",
    "hippoium/core/patch/code_embedder.py",

    # routing
    "hippoium/core/routing/__init__.py",
    "hippoium/core/routing/cost_router.py",
    "hippoium/core/routing/complexity_scorer.py",
    "hippoium/core/routing/fallback_manager.py",

    # utils
    "hippoium/core/utils/__init__.py",
    "hippoium/core/utils/token_counter.py",
    "hippoium/core/utils/text_processor.py",
    "hippoium/core/utils/hasher.py",
    "hippoium/core/utils/serializer.py",

    # ── adapters ─────────────────────────
    "hippoium/adapters/__init__.py",
    "hippoium/adapters/base.py",
    "hippoium/adapters/openai.py",
    "hippoium/adapters/anthropic.py",
    "hippoium/adapters/local.py",
    "hippoium/adapters/http.py",

    # ── factories ────────────────────────
    "hippoium/factories/__init__.py",
    "hippoium/factories/cer_factory.py",
    "hippoium/factories/retriever_factory.py",
    "hippoium/factories/memory_factory.py",

    # ── integrations ─────────────────────
    "hippoium/integrations/__init__.py",
    "hippoium/integrations/langchain_bridge.py",
    "hippoium/integrations/llamaindex_bridge.py",
    "hippoium/integrations/autogen_bridge.py",

    # ── examples_plugins ─────────────────
    "examples_plugins/langchain-hippoium/.keep",
    "examples_plugins/autogen-hippoium/.keep",
    "examples_plugins/llamaindex-hippoium/.keep",
    "examples_plugins/openai-hippoium/.keep",

    # ── examples ─────────────────────────
    "examples/basic_usage/.keep",
    "examples/rag_enhancement/.keep",
    "examples/negative_prompting/.keep",
    "examples/code_generation/.keep",
    "examples/multi_agent_workflow/.keep",

    # ── tests ────────────────────────────
    "tests/unit/.keep",
    "tests/integration/.keep",
    "tests/performance/.keep",

    # ── docs ─────────────────────────────
    "docs/api/.keep",
    "docs/guides/.keep",
    "docs/examples/.keep",

    # ── tools ────────────────────────────
    "tools/benchmarks/.keep",
    "tools/profiling/.keep",
    "tools/migration/.keep",
]

def main() -> None:
    package_dirs: set[Path] = set()

    # 1. 依 FILES 建立檔案並收集所有 ancestor 目錄
    for file_str in PROJECT_FILES:
        path = Path(file_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)

        # 把此檔案的所有祖先目錄加入集合
        for ancestor in path.parents:
            if ancestor == Path('.'):  # 停在專案根
                break
            package_dirs.add(ancestor)

    # 2. 為所有 package 目錄建 __init__.py
    for pkg_dir in package_dirs:
        init_file = pkg_dir / "__init__.py"
        init_file.touch(exist_ok=True)

    print("✅ Hippoium 專案骨架已產生（結構已對齊規劃文件）")

if __name__ == "__main__":
    main()
