"""
Tests for AskUserQuestionTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.ask_question import AskUserQuestionTool


@pytest.fixture
def ask_question_tool() -> AskUserQuestionTool:
    return AskUserQuestionTool()


@pytest.fixture
def mock_context() -> MagicMock:
    return MagicMock()


class TestAskUserQuestionTool:
    """Tests for AskUserQuestionTool."""

    def test_name(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert ask_question_tool.name == "AskUserQuestion"

    def test_aliases(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert ask_question_tool.aliases is None

    def test_search_hint(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert "question" in ask_question_tool.search_hint.lower()

    def test_should_defer(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert ask_question_tool.should_defer is True

    def test_always_load(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert ask_question_tool.always_load is False

    def test_max_result_size_chars(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert ask_question_tool.max_result_size_chars == 100_000

    def test_strict(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert ask_question_tool.strict is False

    def test_description_text(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert "question" in ask_question_tool.description_text.lower()

    def test_prompt_text(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert "question" in ask_question_tool.prompt_text.lower()

    def test_input_schema(self, ask_question_tool: AskUserQuestionTool) -> None:
        schema = ask_question_tool.input_schema
        assert schema["type"] == "object"
        assert "questions" in schema["required"]
        props = schema["properties"]
        assert "questions" in props

    def test_output_schema(self, ask_question_tool: AskUserQuestionTool) -> None:
        schema = ask_question_tool.output_schema
        assert schema["type"] == "object"
        assert "answers" in schema["properties"]

    def test_user_facing_name(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert ask_question_tool.user_facing_name({}) == "Ask"

    def test_is_enabled(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert ask_question_tool.is_enabled() is True

    def test_is_concurrency_safe(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert ask_question_tool.is_concurrency_safe({}) is True

    def test_requires_user_interaction(self, ask_question_tool: AskUserQuestionTool) -> None:
        assert ask_question_tool.requires_user_interaction() is True

    def test_render_tool_use_message(self, ask_question_tool: AskUserQuestionTool) -> None:
        result = ask_question_tool.render_tool_use_message(
            {
                "questions": [
                    {"question": "Which option?", "header": "Choice"}
                ]
            }
        )
        assert "Which option?" in result

    def test_render_tool_use_message_empty(self, ask_question_tool: AskUserQuestionTool) -> None:
        result = ask_question_tool.render_tool_use_message({})
        assert "Asking user" in result

    @pytest.mark.asyncio
    async def test_call_no_elicitation_handler(
        self, ask_question_tool: AskUserQuestionTool, mock_context: MagicMock
    ) -> None:
        mock_context.handle_elicitation = None
        result = await ask_question_tool.call(
            {
                "questions": [
                    {
                        "question": "Pick one",
                        "header": "Option",
                        "options": [
                            {"label": "A", "description": "First"},
                            {"label": "B", "description": "Second"},
                        ],
                    }
                ]
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["answers"] == {}

    @pytest.mark.asyncio
    async def test_call_with_elicitation_handler(
        self, ask_question_tool: AskUserQuestionTool, mock_context: MagicMock
    ) -> None:
        async def mock_elicit(questions):
            return {"Which option?": "A"}

        mock_context.handle_elicitation = mock_elicit
        result = await ask_question_tool.call(
            {
                "questions": [
                    {
                        "question": "Which option?",
                        "header": "Choice",
                        "options": [
                            {"label": "A", "description": "First"},
                            {"label": "B", "description": "Second"},
                        ],
                    }
                ]
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["answers"] == {"Which option?": "A"}

    @pytest.mark.asyncio
    async def test_call_elicitation_error_falls_back(
        self, ask_question_tool: AskUserQuestionTool, mock_context: MagicMock
    ) -> None:
        async def mock_elicit_error(questions):
            raise RuntimeError("Elicitation failed")

        mock_context.handle_elicitation = mock_elicit_error
        result = await ask_question_tool.call(
            {
                "questions": [
                    {
                        "question": "Which?",
                        "header": "H",
                        "options": [
                            {"label": "A", "description": "First"},
                            {"label": "B", "description": "Second"},
                        ],
                    }
                ]
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["answers"] == {}

    def test_map_tool_result_no_answers(self, ask_question_tool: AskUserQuestionTool) -> None:
        result = ask_question_tool.map_tool_result_to_tool_result_block_param(
            {"answers": {}}, "tool-123"
        )
        assert result["tool_use_id"] == "tool-123"
        assert result["content"] == "No answer provided"

    def test_map_tool_result_with_answers(self, ask_question_tool: AskUserQuestionTool) -> None:
        result = ask_question_tool.map_tool_result_to_tool_result_block_param(
            {"answers": {"Which option?": "A", "Color?": "Blue"}}, "tool-456"
        )
        assert result["tool_use_id"] == "tool-456"
        assert "Q: Which option?" in result["content"]
        assert "A: A" in result["content"]
        assert "Q: Color?" in result["content"]
        assert "A: Blue" in result["content"]
