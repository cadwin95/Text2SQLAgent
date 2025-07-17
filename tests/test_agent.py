import os
import sys
import asyncio
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import importlib
nl2sql = importlib.import_module("backend.agent.nl2sql")

class DummyResponse:
    class Choice:
        def __init__(self, content):
            self.message = type('msg', (), {'content': content})
    def __init__(self, content):
        self.choices = [self.Choice(content)]

def test_nl2sql_returns_default_sql():
    sql = asyncio.run(nl2sql.nl2sql("show users"))
    assert sql == "SELECT 1"
