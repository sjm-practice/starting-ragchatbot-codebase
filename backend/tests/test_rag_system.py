"""Tests for RAGSystem.query() in rag_system.py"""
import pytest
from unittest.mock import MagicMock, patch


def make_rag_system():
    """
    Build a RAGSystem with all heavy dependencies mocked out so tests
    don't need a running ChromaDB, Anthropic API key, or embedding model.
    """
    with patch("rag_system.DocumentProcessor"), \
         patch("rag_system.VectorStore"), \
         patch("rag_system.AIGenerator") as MockAI, \
         patch("rag_system.SessionManager") as MockSession, \
         patch("rag_system.ToolManager") as MockToolManager, \
         patch("rag_system.CourseSearchTool"), \
         patch("rag_system.CourseOutlineTool"):

        from config import config
        from rag_system import RAGSystem

        rag = RAGSystem(config)

        # Replace auto-wired mocks with hand-crafted ones for easier control
        rag.ai_generator = MagicMock()
        rag.session_manager = MagicMock()
        rag.tool_manager = MagicMock()

        return rag


class TestRAGSystemQuery:

    def test_query_direct_answer_returns_response_and_empty_sources(self):
        """When Claude answers without tools, sources list is empty."""
        rag = make_rag_system()
        rag.ai_generator.generate_response.return_value = "Python is a programming language."
        rag.tool_manager.get_last_sources.return_value = []

        answer, sources = rag.query("What is Python?")

        assert answer == "Python is a programming language."
        assert sources == []

    def test_query_content_question_returns_sources(self):
        """When the tool was used, sources are retrieved from tool_manager."""
        rag = make_rag_system()
        rag.ai_generator.generate_response.return_value = "RAG combines retrieval with generation."
        rag.tool_manager.get_last_sources.return_value = [
            {"text": "Building RAG Systems - Lesson 1", "url": "https://example.com/lesson/1"}
        ]

        answer, sources = rag.query("Explain RAG")

        assert answer == "RAG combines retrieval with generation."
        assert len(sources) == 1
        assert sources[0]["text"] == "Building RAG Systems - Lesson 1"

    def test_query_resets_sources_after_retrieval(self):
        """tool_manager.reset_sources() is always called after get_last_sources()."""
        rag = make_rag_system()
        rag.ai_generator.generate_response.return_value = "Answer."
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("What is RAG?")

        rag.tool_manager.reset_sources.assert_called_once()

    def test_query_updates_session_history_when_session_id_provided(self):
        """session_manager.add_exchange() is called when a session_id is given."""
        rag = make_rag_system()
        rag.ai_generator.generate_response.return_value = "Some answer."
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("What is fine-tuning?", session_id="sess-123")

        rag.session_manager.add_exchange.assert_called_once_with(
            "sess-123", "What is fine-tuning?", "Some answer."
        )

    def test_query_does_not_update_session_without_session_id(self):
        """session_manager.add_exchange() is NOT called when no session_id is provided."""
        rag = make_rag_system()
        rag.ai_generator.generate_response.return_value = "Some answer."
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("Stateless question")

        rag.session_manager.add_exchange.assert_not_called()

    def test_query_passes_tool_definitions_to_ai_generator(self):
        """generate_response() is called with tools from tool_manager."""
        rag = make_rag_system()
        rag.ai_generator.generate_response.return_value = "Answer."
        rag.tool_manager.get_tool_definitions.return_value = [{"name": "search_course_content"}]
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("What is embeddings?")

        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        assert call_kwargs["tools"] == [{"name": "search_course_content"}]

    def test_query_propagates_exception_from_ai_generator(self):
        """
        If ai_generator.generate_response() raises (e.g. invalid model name →
        Anthropic API error), the exception propagates out of query().
        This is what causes the 500 → 'Query failed' in the frontend.
        """
        rag = make_rag_system()
        rag.ai_generator.generate_response.side_effect = Exception(
            "model: claude-sonnet-4-20250514 not found"
        )

        with pytest.raises(Exception, match="not found"):
            rag.query("What is attention?")

    def test_query_fetches_conversation_history_when_session_id_provided(self):
        """Session history is retrieved before calling generate_response()."""
        rag = make_rag_system()
        rag.session_manager.get_conversation_history.return_value = "User: hi\nAssistant: hello"
        rag.ai_generator.generate_response.return_value = "Answer."
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("Follow-up question", session_id="sess-456")

        rag.session_manager.get_conversation_history.assert_called_once_with("sess-456")
        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] == "User: hi\nAssistant: hello"
