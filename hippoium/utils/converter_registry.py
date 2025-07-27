import importlib
import importlib.util
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

try:
    import yaml
except ImportError:
    yaml = None


# --------------------------------------------------------------------- #
# Abstract base for all converters
# --------------------------------------------------------------------- #
class BaseConverter(ABC):
    name: str                          # e.g. 'mcp', 'a2a'

    # ---- MemoryItem -------------------------------------------------- #
    @abstractmethod
    def convert_memory_item(self, item: Any) -> Any: ...
    @abstractmethod
    def parse_memory_item(self, data: Any) -> Any: ...

    # ---- PromptTemplate --------------------------------------------- #
    @abstractmethod
    def convert_prompt_template(self, template: Any) -> Any: ...
    @abstractmethod
    def parse_prompt_template(self, data: Any) -> Any: ...

    # ---- ToolSpec ---------------------------------------------------- #
    @abstractmethod
    def convert_tool_spec(self, tool: Any) -> Any: ...
    @abstractmethod
    def parse_tool_spec(self, data: Any) -> Any: ...


# --------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------- #
class ConverterRegistry:
    def __init__(self, config: Optional[Union[str, Dict[str, Any]]] = None) -> None:
        # 1️⃣ 讀 YAML or dict
        if config is None:
            path = "config/context_exchange.yaml"
            if yaml is None:
                raise RuntimeError("PyYAML 未安裝且未傳入 config dict")
            with open(path, "r", encoding="utf-8") as f:
                cfg: Dict[str, Any] = yaml.safe_load(f) or {}
        elif isinstance(config, str):
            if yaml is None:
                raise RuntimeError("PyYAML 未安裝且 config 為路徑")
            with open(config, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        else:
            cfg = config or {}

        self.default_llm_provider: Optional[str] = cfg.get("default_llm_provider")
        self.default_output_format: str = cfg.get("default_output_format", "hippoium")
        self.auto_detect_format: bool = cfg.get("auto_detect_format", False)

        self._converters: Dict[str, BaseConverter] = {}
        for fmt, dotted in (cfg.get("converters") or {}).items():
            self._register_from_path(fmt, dotted)

    # ---------- public API ------------------------------------------- #
    def register_converter(self, converter: BaseConverter, *, name: Optional[str] = None) -> None:
        fmt = name or getattr(converter, "name", None)
        if not fmt:
            raise ValueError("Converter 需具備 name")
        self._converters[fmt] = converter

    def get_converter(self, fmt: str) -> Optional[BaseConverter]:
        return self._converters.get(fmt)

    # ---------------- convert_to_format ------------------------------ #
    def convert_to_format(self, fmt: str, obj: Any) -> Any:
        """
        將內部物件 (MemoryItem / PromptTemplate / ToolSpec)
        轉成指定格式 (hippoium/mcp/a2a …) 的資料結構。
        """
        if fmt == "hippoium":
            return obj  # identity
        conv = self.get_converter(fmt)
        if conv is None:
            raise ValueError(f"No converter for format: {fmt}")

        # 粗略判斷型別
        if hasattr(obj, "parameters"):
            return conv.convert_tool_spec(obj)
        if hasattr(obj, "metadata"):
            return conv.convert_memory_item(obj)
        return conv.convert_prompt_template(obj)

    # ---------------- parse_from_format ------------------------------ #
    def parse_from_format(self, fmt: str, data: Any, target: Union[str, type]) -> Any:
        """
        將外部格式資料解析回內部物件。
        `target` 可給型別名稱字串或類別本身 (MemoryItem / PromptTemplate / ToolSpec)。
        """
        if fmt == "hippoium":
            return data
        conv = self.get_converter(fmt)
        if conv is None:
            raise ValueError(f"No converter for format: {fmt}")

        name = target if isinstance(target, str) else getattr(target, "__name__", "")
        name = name.lower()
        if "tool" in name:
            return conv.parse_tool_spec(data)
        if "memory" in name:
            return conv.parse_memory_item(data)
        if "prompt" in name or "template" in name:
            return conv.parse_prompt_template(data)
        raise ValueError(f"Unknown target type: {target}")

    # ---------------- detect_format ---------------------------------- #
    def detect_format(self, data: Any) -> str:
        """
        粗略偵測輸入資料屬於哪種 context 格式。
        回傳 'hippoium' / 'mcp' / 'a2a'。
        """
        if data is None:
            return "hippoium"
        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except Exception:
                return "hippoium"

        if isinstance(data, dict):
            if any(k in data for k in ("resources", "prompts", "tools")):
                return "mcp"
            if any(k in data for k in ("capabilities", "artifactId", "artifacts", "history")):
                return "a2a"
        return "hippoium"

    # ---------------- parse_context (helper) ------------------------- #
    def parse_context(self, data: Any) -> Dict[str, list]:
        """
        根據偵測結果把外部 context 拆解成：
          {memory_items:[…], prompt_templates:[…], tool_specs:[…]}
        """
        fmt = self.detect_format(data)
        if fmt == "hippoium":
            return data if isinstance(data, dict) else {"data": data}
        conv = self.get_converter(fmt)
        if conv is None:
            raise ValueError(f"No converter for format: {fmt}")

        out: Dict[str, list] = {}
        if fmt == "mcp":
            if "resources" in data:
                out["memory_items"] = [conv.parse_memory_item(r) for r in data["resources"]]
            if "prompts" in data:
                out["prompt_templates"] = [conv.parse_prompt_template(p) for p in data["prompts"]]
            if "tools" in data:
                out["tool_specs"] = [conv.parse_tool_spec(t) for t in data["tools"]]
        elif fmt == "a2a":
            if "artifacts" in data:
                out["memory_items"] = [conv.parse_memory_item(a) for a in data["artifacts"]]
            if "capabilities" in data:
                out["tool_specs"] = [conv.parse_tool_spec(c) for c in data["capabilities"]]
            if "history" in data:
                sys_prompts = [m for m in data["history"] if m.get("role") == "system"]
                if sys_prompts:
                    out["prompt_templates"] = [conv.parse_prompt_template(m) for m in sys_prompts]
        return out

    # ---------- internal: import helper ------------------------------ #
    def _register_from_path(self, fmt: str, dotted: str) -> None:
        module_path, cls_name = dotted.rsplit(".", 1)
        module = self._safe_import(module_path)
        cls = getattr(module, cls_name, None)
        if cls is None:
            raise RuntimeError(f"{dotted} 找不到 {cls_name}")
        self.register_converter(cls(), name=fmt)

    def _safe_import(self, module_path: str):
        try:
            return importlib.import_module(module_path)
        except ModuleNotFoundError:
            if not module_path.startswith("hippoium."):
                alt = f"hippoium.{module_path}"
                if importlib.util.find_spec(alt):
                    return importlib.import_module(alt)
            raise