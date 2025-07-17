# PR Plan: Add Agent Query Pipeline

## Summary
Implement minimal NL2SQL agent, new backend endpoint `/api/agent/query` and integrate frontend IDE to use it.

## Tasks
- Create `backend/agent` package with OpenAI-based `nl2sql`.
- Expose `/api/agent/query` endpoint.
- Update FastAPI main app to include new router.
- Extend frontend API utility and IDE page for agent queries.
- Document new endpoint in `PROJECT_STATUS.md`.
- Add unit test for agent module.
- Ensure `pytest -q` passes.
