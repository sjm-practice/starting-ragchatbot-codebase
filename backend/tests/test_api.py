"""Tests for the FastAPI endpoints defined in app.py.

Uses the minimal test app from conftest.py (no static file mount) so tests
run without a frontend/ directory or live ChromaDB/Anthropic connections.
"""
import pytest


class TestQueryEndpoint:

    def test_returns_200_with_answer_and_session(self, test_client, mock_rag_system):
        """Happy path: query returns the AI answer and the session_id."""
        mock_rag_system.query.return_value = ("RAG stands for Retrieval-Augmented Generation.", [])

        resp = test_client.post("/api/query", json={"query": "What is RAG?"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"] == "RAG stands for Retrieval-Augmented Generation."
        assert body["sources"] == []
        assert "session_id" in body

    def test_auto_creates_session_when_not_provided(self, test_client, mock_rag_system):
        """When no session_id is given, one is generated via session_manager."""
        resp = test_client.post("/api/query", json={"query": "Hello"})

        assert resp.status_code == 200
        assert resp.json()["session_id"] == "generated-session-id"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_reuses_provided_session_id(self, test_client, mock_rag_system):
        """When a session_id is supplied it is forwarded to rag.query() and echoed back."""
        resp = test_client.post(
            "/api/query",
            json={"query": "Follow-up question", "session_id": "existing-session"},
        )

        assert resp.status_code == 200
        assert resp.json()["session_id"] == "existing-session"
        # session_manager.create_session should NOT have been called
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_passes_session_id_to_rag_query(self, test_client, mock_rag_system):
        """The session_id (provided or generated) is passed to rag.query()."""
        test_client.post(
            "/api/query",
            json={"query": "What is fine-tuning?", "session_id": "sess-42"},
        )

        mock_rag_system.query.assert_called_once_with("What is fine-tuning?", "sess-42")

    def test_returns_sources_from_rag(self, test_client, mock_rag_system):
        """Sources returned by rag.query() appear in the response."""
        mock_rag_system.query.return_value = (
            "Embeddings are dense vector representations.",
            [{"text": "Course A - Lesson 1", "url": "https://example.com/lesson/1"}],
        )

        resp = test_client.post("/api/query", json={"query": "What are embeddings?"})

        assert resp.status_code == 200
        sources = resp.json()["sources"]
        assert len(sources) == 1
        assert sources[0]["text"] == "Course A - Lesson 1"

    def test_returns_500_when_rag_raises(self, test_client, mock_rag_system):
        """If rag.query() raises, the endpoint returns HTTP 500."""
        mock_rag_system.query.side_effect = RuntimeError("ChromaDB unavailable")

        resp = test_client.post("/api/query", json={"query": "Will this fail?"})

        assert resp.status_code == 500
        assert "ChromaDB unavailable" in resp.json()["detail"]

    def test_returns_422_for_missing_query_field(self, test_client):
        """Omitting the required `query` field produces a 422 Unprocessable Entity."""
        resp = test_client.post("/api/query", json={"session_id": "sess-1"})

        assert resp.status_code == 422


class TestCoursesEndpoint:

    def test_returns_course_stats(self, test_client, mock_rag_system):
        """GET /api/courses returns total_courses and course_titles."""
        resp = test_client.get("/api/courses")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_courses"] == 2
        assert body["course_titles"] == ["Course A", "Course B"]

    def test_calls_get_course_analytics(self, test_client, mock_rag_system):
        """The endpoint delegates to rag.get_course_analytics()."""
        test_client.get("/api/courses")

        mock_rag_system.get_course_analytics.assert_called_once()

    def test_returns_500_when_analytics_raises(self, test_client, mock_rag_system):
        """If get_course_analytics() raises, the endpoint returns HTTP 500."""
        mock_rag_system.get_course_analytics.side_effect = Exception("DB error")

        resp = test_client.get("/api/courses")

        assert resp.status_code == 500
        assert "DB error" in resp.json()["detail"]

    def test_empty_catalog_returns_zero_courses(self, test_client, mock_rag_system):
        """Edge case: no courses loaded yet."""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        resp = test_client.get("/api/courses")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_courses"] == 0
        assert body["course_titles"] == []
