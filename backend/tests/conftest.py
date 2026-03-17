"""Shared test fixtures for RAG chatbot tests."""
import sys
import os
import pytest
from unittest.mock import MagicMock

# Add backend directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vector_store import SearchResults


@pytest.fixture
def sample_search_results():
    """Two results with realistic metadata."""
    return SearchResults(
        documents=[
            "RAG stands for Retrieval-Augmented Generation. It combines a retrieval system with a generative model.",
            "Vector databases store embeddings for semantic similarity search.",
        ],
        metadata=[
            {"course_title": "Building RAG Systems", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "Building RAG Systems", "lesson_number": 2, "chunk_index": 3},
        ],
        distances=[0.15, 0.32],
    )


@pytest.fixture
def empty_search_results():
    """Empty results with no error (no matches)."""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    """Results with a ChromaDB-style error message."""
    return SearchResults.empty(
        "Search error: Number of requested results 5 is greater than number of elements in index 0"
    )


@pytest.fixture
def mock_vector_store(sample_search_results):
    """Mocked VectorStore with sensible defaults."""
    store = MagicMock()
    store.search.return_value = sample_search_results
    store.get_lesson_link.return_value = "https://learn.deeplearning.ai/lesson/1"
    store._resolve_course_name.return_value = "Building RAG Systems"
    store.course_catalog = MagicMock()
    return store
