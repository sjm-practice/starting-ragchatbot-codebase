# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
uv sync
```

> Always use `uv` to manage dependencies and run Python files. Never use `pip` or `python` directly.

**Run the application:**
```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

The app runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

**Environment setup:**
Requires a `.env` file in the project root with `ANTHROPIC_API_KEY=...`. The `.env` file is gitignored — never commit it.

**Force rebuild of ChromaDB:**
ChromaDB persists to `backend/chroma_db/`. To rebuild from scratch, pass `clear_existing=True` to `add_course_folder()` in `rag_system.py`, or delete the `chroma_db/` directory before starting.

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot. All backend code runs from the `backend/` directory — uvicorn is started from there, so imports are relative to that directory.

### Request Flow
1. Frontend (`frontend/script.js`) sends `POST /api/query` with `{ query, session_id }`
2. FastAPI (`app.py`) creates/reuses a session and delegates to `RAGSystem.query()`
3. `RAGSystem` fetches conversation history, then calls `AIGenerator.generate_response()`
4. **Call 1 to Claude**: question + tool definition sent. Claude returns `stop_reason = "tool_use"` if it decides to search, or `"end_turn"` if it can answer directly.
5. If searching: `ToolManager` executes `CourseSearchTool`, which calls `VectorStore.search()` against ChromaDB
6. **Call 2 to Claude**: original question + search results sent. Claude generates final answer.
7. Sources, answer, and session_id returned to frontend.

### Key Architectural Decisions

**Two-call agentic pattern**: Claude decides whether and what to search — the backend does not pre-fetch context. This means general questions are answered without any ChromaDB lookup.

**ChromaDB has two collections**:
- `course_catalog` — one record per course, used to resolve fuzzy course names to exact titles via semantic search before filtering content
- `course_content` — one record per text chunk, used for the actual semantic search

**Deduplication on startup**: `add_course_folder()` compares course titles against existing ChromaDB entries and skips already-loaded courses. Content changes to existing course files are **not** detected — only new titles are picked up.

**Session history is in-memory only**: `SessionManager` stores conversation history in a Python dict. It is not persisted — history is lost on server restart. Only the last `MAX_HISTORY` (default: 2) exchanges are retained per session.

**`lessons_json` workaround**: ChromaDB metadata only supports primitive values. The lessons array for each course is serialized to a JSON string in `course_catalog` metadata and parsed back out on read.

### Configuration
All tuneable parameters are in `backend/config.py`: chunk size/overlap, max search results, conversation history length, model name, and ChromaDB path.

### Course Document Format
Source files in `docs/` must follow this structure for the document processor to parse them correctly:
```
Course Title: [Title]
Course Link: [URL]
Course Instructor: [Name]

Lesson 0: [Title]
Lesson Link: [URL]
[content...]
```
