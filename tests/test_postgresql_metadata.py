import pytest
import sys
import types
import asyncio

# Stub cryptography dependency used by connection_storage
crypto_stub = types.ModuleType("cryptography")
fernet_stub = types.ModuleType("fernet")
class DummyFernet:
    @staticmethod
    def generate_key():
        return b"0" * 32

    def __init__(self, key: bytes):
        pass

    def encrypt(self, data: bytes) -> bytes:
        return data

    def decrypt(self, data: bytes) -> bytes:
        return data

fernet_stub.Fernet = DummyFernet
crypto_stub.fernet = fernet_stub
sys.modules.setdefault("cryptography", crypto_stub)
sys.modules.setdefault("cryptography.fernet", fernet_stub)
sys.modules.setdefault("asyncpg", types.ModuleType("asyncpg"))
sys.modules.setdefault("psycopg2", types.ModuleType("psycopg2"))

from backend.database.handlers.postgresql_handler import PostgreSQLHandler
from backend.database.handlers.base_handler import ConnectionConfig, DatabaseType, QueryResult

def test_get_row_count_metadata(monkeypatch):
    async def run():
        config = ConnectionConfig(id="x", name="t", type=DatabaseType.POSTGRESQL)
        handler = PostgreSQLHandler(config)

        async def mock_execute(query, params=None):
            return QueryResult(
                success=True,
                data=[{"table_name": "t1", "n_live_tup": 5}, {"table_name": "t2", "n_live_tup": None}],
                columns=[],
                row_count=2,
                execution_time=0.0,
            )

        monkeypatch.setattr(handler, "execute_query", mock_execute)
        mapping = await handler._get_row_count_metadata("public")
        assert mapping == {"t1": 5}

    asyncio.run(run())


def test_get_tables_skip_columns(monkeypatch):
    async def run():
        config = ConnectionConfig(id="x", name="t", type=DatabaseType.POSTGRESQL)
        handler = PostgreSQLHandler(config)

        async def mock_row_counts(schema):
            return {"t1": 3}

        async def mock_execute(query, params=None):
            return QueryResult(
                success=True,
                data=[{"name": "t1", "schema_name": "public", "type": "BASE TABLE", "size_bytes": 0, "comment": None}],
                columns=[],
                row_count=1,
                execution_time=0.0,
            )

        called = False

        async def mock_columns(table, schema):
            nonlocal called
            called = True
            return []

        monkeypatch.setattr(handler, "_get_row_count_metadata", mock_row_counts)
        monkeypatch.setattr(handler, "execute_query", mock_execute)
        monkeypatch.setattr(handler, "_get_table_columns", mock_columns)

        tables = await handler.get_tables("public", include_columns=False)
        assert len(tables) == 1
        assert called is False

    asyncio.run(run())
