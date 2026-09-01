"""
tests/conftest.py

Sets fake-but-valid env vars *before* anything imports config.py, so the
test suite runs without a real .env / real Telegram credentials. Also
provides a `test_db` fixture: a fresh temp SQLite database per test,
wired in by monkeypatching database.db's settings reference (not the
real .env-backed one) so tests never touch a real data/*.db file.
"""

from __future__ import annotations

import os

os.environ.setdefault("API_ID", "12345")
os.environ.setdefault("API_HASH", "test_hash_0123456789abcdef")
os.environ.setdefault("PHONE", "+10000000000")
os.environ.setdefault("SESSION_NAME", "test_session")
os.environ.setdefault("DB_PATH", "data/test_job_filter.db")
os.environ.setdefault("LOG_LEVEL", "ERROR")

import dataclasses

import pytest

import database.db as db_module


@pytest.fixture
async def test_db(tmp_path, monkeypatch):
    test_settings = dataclasses.replace(db_module.settings, db_path=str(tmp_path / "test.db"))
    monkeypatch.setattr(db_module, "settings", test_settings)
    await db_module.init_db()
    yield
    await db_module.close_db()
