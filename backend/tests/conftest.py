"""Shared test fixtures for RAG chatbot tests."""
import sys
import os
import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

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


# ---------------------------------------------------------------------------
# API test app helpers
# ---------------------------------------------------------------------------

class _QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class _QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    session_id: str


class _CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


def _build_test_app(rag) -> FastAPI:
    """
    Build a minimal FastAPI app wired to `rag`.

    Mirrors the endpoints in app.py without the static file mount so tests
    can import this without a frontend/ directory present.
    """
    app = FastAPI()

    @app.post("/api/query", response_model=_QueryResponse)
    async def query_documents(request: _QueryRequest):
        try:
            session_id = request.session_id or rag.session_manager.create_session()
            answer, sources = rag.query(request.query, session_id)
            return _QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=_CourseStats)
    async def get_course_stats():
        try:
            analytics = rag.get_course_analytics()
            return _CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def mock_rag_system():
    """Mocked RAGSystem with sensible default return values."""
    rag = MagicMock()
    rag.query.return_value = ("Test answer.", [])
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Course A", "Course B"],
    }
    rag.session_manager.create_session.return_value = "generated-session-id"
    return rag


@pytest.fixture
def test_client(mock_rag_system):
    """TestClient backed by the minimal test app with a mocked RAGSystem."""
    return TestClient(_build_test_app(mock_rag_system))


@pytest.fixture
def mock_vector_store(sample_search_results):
    """Mocked VectorStore with sensible defaults."""
    store = MagicMock()
    store.search.return_value = sample_search_results
    store.get_lesson_link.return_value = "https://learn.deeplearning.ai/lesson/1"
    store._resolve_course_name.return_value = "Building RAG Systems"
    store.course_catalog = MagicMock()
    return store
