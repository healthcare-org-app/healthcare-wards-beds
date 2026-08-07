"""Kafka consumers for wards-beds-service.

One handler per subscribed topic. Handlers are best-effort logging plus
audit — services override this file to implement real cross-domain behavior.
"""
from __future__ import annotations

import logging

from healthcare_common.audit import emit_audit

log = logging.getLogger("wards-beds-service.consumers")


def register(svc) -> None:
    bus = svc.bus

    @bus.on("encounter.started")
    def _on_encounter_started(envelope: dict) -> None:
        log.info("wards-beds-service: received encounter.started id=%s", envelope.get("id"))
        emit_audit(bus, action="consume.encounter.started", actor="system:wards-beds-service",
                   target=None, details={"envelope_id": envelope.get("id")})

    @bus.on("encounter.ended")
    def _on_encounter_ended(envelope: dict) -> None:
        log.info("wards-beds-service: received encounter.ended id=%s", envelope.get("id"))
        emit_audit(bus, action="consume.encounter.ended", actor="system:wards-beds-service",
                   target=None, details={"envelope_id": envelope.get("id")})

