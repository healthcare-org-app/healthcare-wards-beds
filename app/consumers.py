"""Kafka consumers for wards-beds-service.

One handler per subscribed topic. Real handlers write to this service's own
database and/or publish follow-up events; stub handlers just log + audit.
"""
from __future__ import annotations

import logging

from psycopg.types.json import Json

from healthcare_common.audit import emit_audit

log = logging.getLogger("wards-beds-service.consumers")

TABLE = "wards_beds"


def register(svc) -> None:
    bus = svc.bus
    db = svc.db
    clients = svc.clients

    @bus.on("encounter.started")
    def _on_encounter_started(envelope: dict) -> None:
        data = envelope.get("data") or {}
        try:
                    # Occupy a bed if one is assigned.
                    bed = data.get("bed_id")
                    if bed:
                        db.execute(f"UPDATE {TABLE} SET status='occupied', updated_at=now() "
                                   f"WHERE id = %s", (int(bed),))
        except Exception as e:
            log.exception("wards-beds-service/encounter.started handler failed: %s", e)
        emit_audit(bus, action="consume.encounter.started", actor="system:wards-beds-service",
                   target=None, details={"envelope_id": envelope.get("id")})

    @bus.on("encounter.ended")
    def _on_encounter_ended(envelope: dict) -> None:
        data = envelope.get("data") or {}
        try:
                    bed = data.get("bed_id")
                    if bed:
                        db.execute(f"UPDATE {TABLE} SET status='vacant', updated_at=now() "
                                   f"WHERE id = %s", (int(bed),))
        except Exception as e:
            log.exception("wards-beds-service/encounter.ended handler failed: %s", e)
        emit_audit(bus, action="consume.encounter.ended", actor="system:wards-beds-service",
                   target=None, details={"envelope_id": envelope.get("id")})

