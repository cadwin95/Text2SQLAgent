# Codex Agent Guidelines

This repository contains the **Text2SQL Agent** project.

## Development Rules
- Follow the existing folder structure (`backend/`, `frontend/`, etc.).
- Keep Python code formatted with basic PEP8 style.
- Any new feature or endpoint should be briefly documented in `PROJECT_STATUS.md`.
- Each pull request must include a short markdown plan under `plans/` describing the change.
- After modifications run `pytest -q` from the repository root.
- Prefer asynchronous FastAPI patterns when touching backend code.

