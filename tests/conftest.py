"""Fake DB + fake bus so tests don't require Postgres/Kafka."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pytest
from flask import Flask

from healthcare_common.tracing import request_id_middleware


class FakeDB:
    def __init__(self):
        self.rows: dict[int, dict] = {}
        self._next_id = 1000

    def query(self, sql, params=()):
        return self.exec(sql, params)[0]
    def query_one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None
    def execute(self, sql, params=()):
        return self.exec(sql, params)[2]

    def exec(self, sql, params):
        s = " ".join(sql.split()).lower()
        if s.startswith("create table") or s.startswith("create index"):
            return [], None, 0
        if s.startswith("select count(*)"):
            # honor a WHERE clause loosely: return current row count
            return [{"n": len(self.rows)}], "count", len(self.rows)
        if "insert into" in s and "returning *" in s:
            data = params[0]
            rid = self._next_id; self._next_id += 1
            now = datetime.now(timezone.utc)
            payload = data.obj if hasattr(data, "obj") else data
            row = {"id": rid, "data": payload, "status": "active",
                   "created_at": now, "updated_at": now}
            self.rows[rid] = row
            return [row], "row", 1
        if s.startswith("select * from") and "where id" in s:
            pid = params[0]
            return ([self.rows[pid]] if pid in self.rows else []), "row", 1
        if "order by id limit" in s:
            limit, offset = params[-2], params[-1]
            items = sorted(self.rows.values(), key=lambda r: r["id"])[offset:offset+limit]
            return items, "row", len(items)
        if s.startswith("update") and "set data" in s and "returning *" in s:
            data, status, pid = params
            r = self.rows.get(pid)
            if not r: return [], "row", 0
            r["data"] = data.obj if hasattr(data, "obj") else data
            r["status"] = status
            r["updated_at"] = datetime.now(timezone.utc)
            return [r], "row", 1
        if s.startswith("update") and "status='inactive'" in s and "returning *" in s:
            pid = params[0]
            r = self.rows.get(pid)
            if not r: return [], "row", 0
            r["status"] = "inactive"
            r["updated_at"] = datetime.now(timezone.utc)
            return [r], "row", 1
        raise NotImplementedError(f"FakeDB: unhandled SQL: {sql}")


@dataclass
class FakeBus:
    published: list = field(default_factory=list)
    handlers: dict = field(default_factory=dict)

    def publish(self, topic, *, key, value):
        self.published.append((topic, key, value))
    def on(self, topic):
        def _dec(fn): self.handlers[topic] = fn; return fn
        return _dec
    def start(self): pass
    def stop(self, *a): pass


@dataclass
class FakeService:
    app: Flask
    bus: FakeBus
    db: FakeDB
    clients: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    name: str = "test-service"


@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "1")
    app = Flask("test")
    request_id_middleware(app)
    return FakeService(app=app, bus=FakeBus(), db=FakeDB())


@pytest.fixture
def client(svc):
    from app.routes import build_blueprint
    from app.consumers import register as register_consumers
    svc.app.register_blueprint(build_blueprint(svc))
    register_consumers(svc)
    with svc.app.test_client() as c:
        yield c
