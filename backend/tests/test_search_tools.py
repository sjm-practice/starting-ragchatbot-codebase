"""Tests for CourseSearchTool.execute() in search_tools.py"""
import pytest
from unittest.mock import MagicMock, patch

from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchToolExecute:

    def test_execute_returns_formatted_results(self, mock_vector_store, sample_search_results):
        """Happy path: search returns docs, execute() returns a non-empty formatted string."""
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="What is RAG?")

        assert isinstance(result, str)
        assert len(result) > 0
        # Formatted results should include the course title header
        assert "Building RAG Systems" in result

    def test_execute_populates_last_sources(self, mock_vector_store, sample_search_results):
        """After a successful execute(), last_sources contains text/url dicts."""
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="What is RAG?")

        assert len(tool.last_sources) == 2
        assert tool.last_sources[0]["text"] == "Building RAG Systems - Lesson 1"
        assert tool.last_sources[0]["url"] == "https://learn.deeplearning.ai/lesson/1"

    def test_execute_empty_results_returns_no_content_message(self, mock_vector_store, empty_search_results):
        """When search returns empty results, execute() returns a descriptive string, not an exception."""
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="something obscure")

        assert "No relevant content found" in result
        assert isinstance(result, str)

    def test_execute_error_results_returns_error_string(self, mock_vector_store, error_search_results):
        """When SearchResults.error is set, execute() returns the error string (not raises)."""
        mock_vector_store.search.return_value = error_search_results
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="anything")

        assert "Search error" in result
        assert isinstance(result, str)

    def test_execute_with_course_filter_passes_course_name(self, mock_vector_store):
        """course_name param is forwarded to VectorStore.search()."""
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="attention mechanism", course_name="Transformer Course")

        mock_vector_store.search.assert_called_once_with(
            query="attention mechanism",
            course_name="Transformer Course",
            lesson_number=None,
        )

    def test_execute_with_lesson_filter_passes_lesson_number(self, mock_vector_store):
        """lesson_number param is forwarded to VectorStore.search()."""
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="embeddings", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="embeddings",
            course_name=None,
            lesson_number=3,
        )

    def test_execute_n_results_chromadb_error_handled_gracefully(self, mock_vector_store):
        """
        Simulates the ChromaDB 'n_results > collection count' ValueError being
        caught and returned as a SearchResults error string — not a bare exception.
        """
        mock_vector_store.search.return_value = SearchResults.empty(
            "Search error: Number of requested results 5 is greater than number of elements in index 2"
        )
        tool = CourseSearchTool(mock_vector_store)

        # Should NOT raise; the error is surfaced as a string
        result = tool.execute(query="What is fine tuning?")
        assert isinstance(result, str)
        assert "Search error" in result

    def test_empty_results_with_course_filter_message_includes_course(self, mock_vector_store, empty_search_results):
        """'No relevant content found in course X' when course_name is specified."""
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="something", course_name="My Course")

        assert "My Course" in result

    def test_last_sources_empty_after_error(self, mock_vector_store, error_search_results):
        """last_sources should remain empty when the search returned an error."""
        mock_vector_store.search.return_value = error_search_results
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="anything")

        assert tool.last_sources == []
