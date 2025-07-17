# PR Plan: Optimize PostgreSQL table loading

## Summary
Use metadata from `pg_stat_all_tables` to estimate row counts instead of running
`SELECT COUNT(*)` for every table. Tables missing metadata are skipped.

## Tasks
- Add helper `_get_row_count_metadata` in `PostgreSQLHandler`.
- Update `get_tables` and `get_table_info` to rely on metadata counts.
- Document improvement in `PROJECT_STATUS.md`.
- Ensure `pytest -q` passes.
