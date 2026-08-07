"""HTTP routes for wards-beds-service.

Generic CRUD over the `wards_beds` table. Every mutating endpoint publishes a
domain event (audit.event) and an audit event; reads publish audit only.

To customize: add domain-specific endpoints below the CRUD block.
"""
from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request, g
from psycopg.types.json import Json

from healthcare_common.audit import emit_audit
from healthcare_common.auth import require_auth
from healthcare_common.http import ServiceUnavailable, json_or_raise


TABLE = "wards_beds"
RESOURCE = "wards_beds"
CREATED_EVENT = ""
UPDATED_EVENT = ""


def build_blueprint(svc) -> Blueprint:
    bp = Blueprint(RESOURCE, __name__, url_prefix=f"/api/{RESOURCE}")
    db, bus, clients = svc.db, svc.bus, svc.clients

    def _actor() -> str:
        return getattr(g, "principal", {}).get("sub", "anonymous")

    def _row_json(row: dict) -> dict:
        return {
            "id": row["id"],
            "status": row["status"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
            **(row["data"] or {}),
        }

    @bp.get("/")
    @require_auth(scopes=[f"{RESOURCE}.read"])
    def list_records():
        try:
            offset = int(request.args.get("offset", 0))
            limit = min(int(request.args.get("limit", 50)), 500)
        except ValueError:
            return jsonify({"error": "offset/limit must be integers"}), 400

        wheres, params = [], []
        for k, v in request.args.items():
            if k in ("limit", "offset"):
                continue
            if k == "status":
                wheres.append("status = %s"); params.append(v)
            else:
                wheres.append("data->>%s = %s"); params.extend([k, v])

        clause = ("WHERE " + " AND ".join(wheres)) if wheres else ""
        rows = db.query(f"SELECT * FROM {TABLE} {clause} ORDER BY id LIMIT %s OFFSET %s",
                        tuple(params + [limit, offset]))
        total = db.query_one(f"SELECT count(*) AS n FROM {TABLE} {clause}", tuple(params))["n"]
        emit_audit(bus, action=f"{RESOURCE}.list", actor=_actor(),
                   details={"filters": dict(request.args), "returned": len(rows)})
        return jsonify({"count": total, "items": [_row_json(r) for r in rows]})

    @bp.post("/")
    @require_auth(scopes=[f"{RESOURCE}.write"])
    def create_record():
        payload = request.get_json(silent=True) or {}
        payload.pop("id", None)
        row = db.query_one(
            f"INSERT INTO {TABLE} (data) VALUES (%s) RETURNING *",
            (Json(payload),),
        )
        record = _row_json(row)
        if CREATED_EVENT:
            bus.publish(CREATED_EVENT, key=str(row["id"]), value=record)
        emit_audit(bus, action=f"{RESOURCE}.create", actor=_actor(),
                   target=f"{RESOURCE}:{row['id']}")
        return jsonify(record), 201

    @bp.get("/<int:record_id>")
    @require_auth(scopes=[f"{RESOURCE}.read"])
    def get_record(record_id: int):
        row = db.query_one(f"SELECT * FROM {TABLE} WHERE id = %s", (record_id,))
        if not row:
            return jsonify({"error": f"{RESOURCE} {record_id} not found"}), 404
        emit_audit(bus, action=f"{RESOURCE}.read", actor=_actor(),
                   target=f"{RESOURCE}:{record_id}")
        return jsonify(_row_json(row))

    @bp.put("/<int:record_id>")
    @bp.patch("/<int:record_id>")
    @require_auth(scopes=[f"{RESOURCE}.write"])
    def update_record(record_id: int):
        existing = db.query_one(f"SELECT * FROM {TABLE} WHERE id = %s", (record_id,))
        if not existing:
            return jsonify({"error": f"{RESOURCE} {record_id} not found"}), 404
        payload = request.get_json(silent=True) or {}
        payload.pop("id", None)
        new_status = payload.pop("status", existing["status"])
        merged = {**(existing["data"] or {}), **payload}
        row = db.query_one(
            f"""UPDATE {TABLE} SET data=%s, status=%s, updated_at=now()
                WHERE id=%s RETURNING *""",
            (Json(merged), new_status, record_id),
        )
        record = _row_json(row)
        if UPDATED_EVENT:
            bus.publish(UPDATED_EVENT, key=str(record_id), value=record)
        emit_audit(bus, action=f"{RESOURCE}.update", actor=_actor(),
                   target=f"{RESOURCE}:{record_id}",
                   details={"fields": list(payload.keys())})
        return jsonify(record)

    @bp.delete("/<int:record_id>")
    @require_auth(scopes=[f"{RESOURCE}.write"])
    def delete_record(record_id: int):
        row = db.query_one(
            f"""UPDATE {TABLE} SET status='inactive', updated_at=now()
                WHERE id=%s RETURNING *""",
            (record_id,),
        )
        if not row:
            return jsonify({"error": f"{RESOURCE} {record_id} not found"}), 404
        if UPDATED_EVENT:
            bus.publish(UPDATED_EVENT, key=str(record_id), value=_row_json(row))
        emit_audit(bus, action=f"{RESOURCE}.deactivate", actor=_actor(),
                   target=f"{RESOURCE}:{record_id}")
        return jsonify({"deactivated": record_id})



    return bp
