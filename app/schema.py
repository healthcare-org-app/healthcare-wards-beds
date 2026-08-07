"""Table for wards-beds-service."""
from __future__ import annotations

from healthcare_common.db import DBPool

TABLE = "wards_beds"


def create_tables(db: DBPool) -> None:
    db.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id          BIGSERIAL PRIMARY KEY,
            data        JSONB NOT NULL,
            status      TEXT NOT NULL DEFAULT 'active',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    db.execute(f"CREATE INDEX IF NOT EXISTS {TABLE}_status_idx ON {TABLE}(status)")
    db.execute(f"CREATE INDEX IF NOT EXISTS {TABLE}_data_gin ON {TABLE} USING gin (data jsonb_path_ops)")
