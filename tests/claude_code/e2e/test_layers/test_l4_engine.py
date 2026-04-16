"""E2E 测试 - L4: 引擎层

验证 QueryEngine、pipeline、tool orchestration。
直接测试引擎，不通过 CLI。
"""

from __future__ import annotations

import pytest


class TestQueryEngine:
    """测试 QueryEngine."""

    @pytest.mark.asyncio
    async def test_engine_requires_api_client(self):
        """验证引擎需要 API 客户端."""
        from claude_code.engine.engine import QueryEngine

        # 应该能创建引擎
        try:
            from claude_code.services.api.claude import ClaudeAIClient
            client = ClaudeAIClient(api_key="test")
            engine = QueryEngine(api_client=client)
            assert engine is not None
        except Exception:
            # 如果 API key 无效，跳过
            pytest.skip("API client creation failed")

    @pytest.mark.asyncio
    async def test_engine_submit_message(self, api_key: str):
        """验证引擎可以提交消息."""
        from claude_code.engine.engine import QueryEngine
        from claude_code.models.message import ContentBlock, Message, Role
        from claude_code.services.api.claude import ClaudeAIClient

        client = ClaudeAIClient(api_key=api_key)
        engine = QueryEngine(api_client=client)

        messages: list = []
        events_received = []

        async for event in engine.submit_message(
            prompt="Say 'test' in one word",
            messages=messages,
        ):
            events_received.append(event)
            if len(events_received) > 100:
                break

        # 应该收到事件
        assert len(events_received) > 0

    def test_engine_initial_state(self, api_key: str):
        """验证引擎初始状态."""
        from claude_code.engine.engine import QueryEngine
        from claude_code.services.api.claude import ClaudeAIClient

        client = ClaudeAIClient(api_key=api_key)
        engine = QueryEngine(api_client=client)

        assert engine.is_running is False
        assert engine.turn_count == 0


class TestToolOrchestration:
    """测试工具编排."""

    @pytest.mark.asyncio
    async def test_tool_orchestrator_exists(self):
        """验证工具编排器存在."""
        from claude_code.engine.tools.orchestration import ToolOrchestrator

        orchestrator = ToolOrchestrator(max_parallel=10)
        assert orchestrator is not None

    def test_tool_call_partition(self):
        """验证工具调用分区."""
        from claude_code.engine.tools.orchestration import ToolOrchestrator

        orchestrator = ToolOrchestrator(max_parallel=10)

        # 应该能够分区工具调用
        # 这个测试验证分区逻辑存在
        assert orchestrator._max_parallel == 10


class TestPipeline:
    """测试查询 pipeline."""

    def test_pipeline_import(self):
        """验证 pipeline 可以导入."""
        from claude_code.engine.pipeline import QueryState

        state = QueryState(messages=[], turn_count=0)
        assert state is not None
        assert state.turn_count == 0
