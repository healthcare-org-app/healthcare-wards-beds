"""Idempotent seed data for wards-beds-service. Empty by default; customize per service."""
from __future__ import annotations

import logging

from healthcare_common.db import db_pool
from .schema import create_tables

log = logging.getLogger("wards-beds-service.seed")


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db = db_pool()
    create_tables(db)


if __name__ == "__main__":
    run()
