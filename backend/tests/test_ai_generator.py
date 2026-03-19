"""Tests for AIGenerator in ai_generator.py"""
import re
import pytest
from unittest.mock import MagicMock, patch, call

from ai_generator import AIGenerator
from config import config


# ---------------------------------------------------------------------------
# Helpers: build mock Anthropic response objects
# ---------------------------------------------------------------------------

def make_text_response(text="Here is the answer."):
    """Simulates a Claude response with stop_reason='end_turn'."""
    block = MagicMock()
    block.type = "text"
    block.text = text

    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


def make_tool_use_response(tool_name="search_course_content", tool_input=None, tool_id="tu_abc123"):
    """Simulates a Claude response with stop_reason='tool_use'."""
    if tool_input is None:
        tool_input = {"query": "What is RAG?"}

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.input = tool_input
    tool_block.id = tool_id

    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [tool_block]
    return response


# ---------------------------------------------------------------------------
# Model name validation
# ---------------------------------------------------------------------------

# Allowlist of known valid Anthropic model IDs (update when new models are released)
VALID_ANTHROPIC_MODELS = {
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
}

class TestModelName:

    def test_model_name_is_valid(self):
        """
        ANTHROPIC_MODEL must be a known valid Anthropic model ID.
        'claude-sonnet-4-20250514' is NOT valid — it causes a 400/404 from the
        Anthropic API, which propagates as an uncaught exception → HTTP 500 →
        frontend shows 'Query failed'.

        Valid IDs: claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5-20251001
        """
        model = config.ANTHROPIC_MODEL
        assert model in VALID_ANTHROPIC_MODELS, (
            f"ANTHROPIC_MODEL='{model}' is not a recognized Anthropic model ID. "
            f"Valid options: {sorted(VALID_ANTHROPIC_MODELS)}. "
            f"Update ANTHROPIC_MODEL in backend/config.py."
        )


# ---------------------------------------------------------------------------
# generate_response() — direct answer path
# ---------------------------------------------------------------------------

class TestGenerateResponseDirectAnswer:

    @pytest.fixture
    def generator(self):
        with patch("ai_generator.anthropic.Anthropic") as MockAnthropic:
            instance = MockAnthropic.return_value
            yield AIGenerator(api_key="test-key", model="claude-sonnet-4-6"), instance

    def test_returns_text_on_end_turn(self, generator):
        gen, mock_client = generator
        mock_client.messages.create.return_value = make_text_response("Direct answer here.")

        result = gen.generate_response(query="What is Python?")
        assert result == "Direct answer here."

    def test_tools_are_not_added_when_not_provided(self, generator):
        gen, mock_client = generator
        mock_client.messages.create.return_value = make_text_response()

        gen.generate_response(query="Hello")
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "tools" not in call_kwargs
        assert "tool_choice" not in call_kwargs

    def test_tools_and_tool_choice_sent_when_provided(self, generator):
        gen, mock_client = generator
        mock_client.messages.create.return_value = make_text_response()

        fake_tools = [{"name": "search_course_content"}]
        gen.generate_response(query="Tell me about RAG", tools=fake_tools)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["tools"] == fake_tools
        assert call_kwargs["tool_choice"] == {"type": "auto"}

    def test_query_appears_in_user_message(self, generator):
        gen, mock_client = generator
        mock_client.messages.create.return_value = make_text_response()

        gen.generate_response(query="What is attention?")
        call_kwargs = mock_client.messages.create.call_args[1]
        messages = call_kwargs["messages"]
        assert any("What is attention?" in str(m) for m in messages)


# ---------------------------------------------------------------------------
# generate_response() — single tool-use round
# ---------------------------------------------------------------------------

class TestGenerateResponseToolUse:

    @pytest.fixture
    def generator_with_tool(self):
        with patch("ai_generator.anthropic.Anthropic") as MockAnthropic:
            client_instance = MockAnthropic.return_value
            # First call returns tool_use, second returns the final text
            tool_response = make_tool_use_response()
            final_response = make_text_response("RAG combines retrieval with generation.")
            client_instance.messages.create.side_effect = [tool_response, final_response]

            tool_manager = MagicMock()
            tool_manager.execute_tool.return_value = "RAG stands for Retrieval-Augmented Generation."

            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            yield gen, client_instance, tool_manager

    def test_tool_manager_execute_tool_called(self, generator_with_tool):
        gen, mock_client, tool_manager = generator_with_tool
        gen.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )
        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="What is RAG?"
        )

    def test_final_response_text_returned(self, generator_with_tool):
        gen, mock_client, tool_manager = generator_with_tool
        result = gen.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )
        assert result == "RAG combines retrieval with generation."

    def test_two_api_calls_made(self, generator_with_tool):
        gen, mock_client, tool_manager = generator_with_tool
        gen.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )
        assert mock_client.messages.create.call_count == 2

    def test_second_api_call_includes_tools(self, generator_with_tool):
        """After round 1 there is still a round remaining, so tools must be present in Call 2."""
        gen, mock_client, tool_manager = generator_with_tool
        gen.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs
        assert "tool_choice" in second_call_kwargs

    def test_tool_result_message_has_correct_format(self, generator_with_tool):
        """
        The tool result appended as a user message must include:
          type='tool_result', tool_use_id, content
        This is the format the Anthropic API expects.
        """
        gen, mock_client, tool_manager = generator_with_tool
        gen.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]

        # Find the user message containing tool results
        tool_result_messages = [
            m for m in messages
            if m.get("role") == "user" and isinstance(m.get("content"), list)
        ]
        assert len(tool_result_messages) == 1, "Expected one user message with tool results"

        tool_result_content = tool_result_messages[0]["content"]
        assert len(tool_result_content) == 1
        result_block = tool_result_content[0]
        assert result_block["type"] == "tool_result"
        assert result_block["tool_use_id"] == "tu_abc123"
        assert result_block["content"] == "RAG stands for Retrieval-Augmented Generation."


# ---------------------------------------------------------------------------
# generate_response() — two sequential tool-use rounds
# ---------------------------------------------------------------------------

class TestTwoRoundToolUse:

    @pytest.fixture
    def two_round_setup(self):
        with patch("ai_generator.anthropic.Anthropic") as MockAnthropic:
            client_instance = MockAnthropic.return_value
            r1 = make_tool_use_response(tool_id="tu_round1", tool_input={"query": "outline of course X"})
            r2 = make_tool_use_response(tool_id="tu_round2", tool_input={"query": "same topic as lesson 4"})
            final = make_text_response("Here is the complete answer.")
            client_instance.messages.create.side_effect = [r1, r2, final]

            tool_manager = MagicMock()
            tool_manager.execute_tool.return_value = "some result"

            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            yield gen, client_instance, tool_manager

    def _run(self, gen, tool_manager):
        return gen.generate_response(
            query="Find a course covering the same topic as lesson 4 of course X",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

    def test_three_api_calls_made_on_two_rounds(self, two_round_setup):
        gen, mock_client, tool_manager = two_round_setup
        self._run(gen, tool_manager)
        assert mock_client.messages.create.call_count == 3

    def test_tool_manager_called_twice(self, two_round_setup):
        gen, mock_client, tool_manager = two_round_setup
        self._run(gen, tool_manager)
        assert tool_manager.execute_tool.call_count == 2

    def test_final_text_returned_after_two_rounds(self, two_round_setup):
        gen, mock_client, tool_manager = two_round_setup
        result = self._run(gen, tool_manager)
        assert result == "Here is the complete answer."

    def test_second_call_includes_tools(self, two_round_setup):
        """Call 2 must include tools — round 1 consumed, round 2 still available."""
        gen, mock_client, tool_manager = two_round_setup
        self._run(gen, tool_manager)
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs
        assert "tool_choice" in second_call_kwargs

    def test_synthesis_call_excludes_tools(self, two_round_setup):
        """Call 3 (synthesis after both rounds) must not include tools."""
        gen, mock_client, tool_manager = two_round_setup
        self._run(gen, tool_manager)
        third_call_kwargs = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs
        assert "tool_choice" not in third_call_kwargs

    def test_message_history_has_both_rounds(self, two_round_setup):
        """Call 3 messages must contain the full two-round history:
        original user msg + assistant r1 + user tool_result r1
        + assistant r2 + user tool_result r2 = 5 messages total."""
        gen, mock_client, tool_manager = two_round_setup
        self._run(gen, tool_manager)
        third_call_kwargs = mock_client.messages.create.call_args_list[2][1]
        messages = third_call_kwargs["messages"]
        assert len(messages) == 5


# ---------------------------------------------------------------------------
# generate_response() — tool execution error handling
# ---------------------------------------------------------------------------

class TestToolExecutionError:

    @pytest.fixture
    def error_setup(self):
        with patch("ai_generator.anthropic.Anthropic") as MockAnthropic:
            client_instance = MockAnthropic.return_value
            tool_response = make_tool_use_response()
            final_response = make_text_response("I was unable to retrieve the information.")
            client_instance.messages.create.side_effect = [tool_response, final_response]

            tool_manager = MagicMock()
            tool_manager.execute_tool.side_effect = Exception("DB unavailable")

            gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-6")
            yield gen, client_instance, tool_manager

    def _run(self, gen, tool_manager):
        return gen.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

    def test_returns_string_on_tool_error(self, error_setup):
        gen, mock_client, tool_manager = error_setup
        result = self._run(gen, tool_manager)
        assert isinstance(result, str)

    def test_two_api_calls_on_error(self, error_setup):
        """Error terminates the loop immediately — no second tool round attempted."""
        gen, mock_client, tool_manager = error_setup
        self._run(gen, tool_manager)
        assert mock_client.messages.create.call_count == 2

    def test_error_result_block_sent_to_claude(self, error_setup):
        """Even on failure a tool_result block must be sent — the API requires it."""
        gen, mock_client, tool_manager = error_setup
        self._run(gen, tool_manager)
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]

        tool_result_messages = [
            m for m in messages
            if m.get("role") == "user" and isinstance(m.get("content"), list)
        ]
        assert len(tool_result_messages) == 1
        result_block = tool_result_messages[0]["content"][0]
        assert result_block["type"] == "tool_result"
        assert result_block["tool_use_id"] == "tu_abc123"

    def test_synthesis_call_excludes_tools_on_error(self, error_setup):
        """After an error, the follow-up synthesis call must not include tools."""
        gen, mock_client, tool_manager = error_setup
        self._run(gen, tool_manager)
        second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
        assert "tools" not in second_call_kwargs
        assert "tool_choice" not in second_call_kwargs
