# PR Plan: Optional Column Loading

## Summary
Add the ability to load tables without column information to speed up initial schema queries.  New API query parameter `includeColumns` controls this behaviour.

## Tasks
- Extend `BaseDatabaseHandler` and `ConnectionManager` methods with `include_columns` flag.
- Update individual database handlers to skip column queries when the flag is `False`.
- Expose `includeColumns` query param on schema endpoints and update frontend utility.
- Document the change in `PROJECT_STATUS.md`.
- Add unit tests for the new flag and for row count metadata.
- Ensure `pytest -q` passes.
