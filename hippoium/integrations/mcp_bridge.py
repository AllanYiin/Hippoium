# integrations/mcp_bridge.py
from hippoium.ports import ContextEngineProtocol
from hippoium.core.builder import PromptBuilder
from mcp_sdk import ContextRecord, ContextQuery, ContextBundle

class MCPBridge:
    def __init__(self, engine: ContextEngineProtocol):
        self.engine = engine
        self.builder = PromptBuilder()

    # 1️⃣ 寫入
    def record_context(self, record: ContextRecord):
        self.engine.write_turn(
            role=record.role,
            content=record.content,
            metadata=record.meta,
        )

    # 2️⃣ 讀取
    def query_context(self, query: ContextQuery) -> ContextBundle:
        # scope 可能是 "user" / "task" / "topic"
        ctx = self.engine.get_context_for_scope(
            scope=query.scope,
            key=query.key,
            query_text=query.prompt,
            filters=query.filters,      # e.g. exclude_err=True
        )
        prompt = self.builder.build(
            template_id=query.template_id,
            context=ctx,
            user_query=query.prompt,
        )
        return ContextBundle(messages=prompt)
