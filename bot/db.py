"""SQLite helpers for device inventory."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_chat_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    model TEXT,
    serial TEXT,
    imei TEXT,
    phone TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_devices_owner ON devices(owner_chat_id);
CREATE INDEX IF NOT EXISTS idx_devices_name ON devices(name);
CREATE INDEX IF NOT EXISTS idx_devices_serial ON devices(serial);
CREATE INDEX IF NOT EXISTS idx_devices_imei ON devices(imei);
CREATE INDEX IF NOT EXISTS idx_devices_phone ON devices(phone);
"""


class DeviceDB:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def add_device(
        self,
        owner_chat_id: int,
        name: str,
        model: str | None = None,
        serial: str | None = None,
        imei: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO devices (owner_chat_id, name, model, serial, imei, phone, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    owner_chat_id,
                    name.strip(),
                    (model or "").strip() or None,
                    (serial or "").strip() or None,
                    (imei or "").strip() or None,
                    (phone or "").strip() or None,
                    (notes or "").strip() or None,
                ),
            )
            return int(cur.lastrowid)

    def list_devices(self, owner_chat_id: int, limit: int = 20) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM devices
                WHERE owner_chat_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (owner_chat_id, limit),
            ).fetchall()
            return list(rows)

    def search(self, owner_chat_id: int, query: str, limit: int = 10) -> list[sqlite3.Row]:
        q = f"%{query.strip()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM devices
                WHERE owner_chat_id = ?
                  AND (
                    name LIKE ? COLLATE NOCASE
                    OR IFNULL(model, '') LIKE ? COLLATE NOCASE
                    OR IFNULL(serial, '') LIKE ? COLLATE NOCASE
                    OR IFNULL(imei, '') LIKE ? COLLATE NOCASE
                    OR IFNULL(phone, '') LIKE ? COLLATE NOCASE
                    OR IFNULL(notes, '') LIKE ? COLLATE NOCASE
                  )
                ORDER BY id DESC
                LIMIT ?
                """,
                (owner_chat_id, q, q, q, q, q, q, limit),
            ).fetchall()
            return list(rows)

    def get_by_id(self, owner_chat_id: int, device_id: int) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM devices WHERE id = ? AND owner_chat_id = ?",
                (device_id, owner_chat_id),
            ).fetchone()

    def get_by_device_id(self, owner_chat_id: int, device_id: str) -> sqlite3.Row | None:
        """Lookup by numeric DB id, else exact serial / IMEI / phone."""
        key = device_id.strip()
        if not key:
            return None
        if key.isdigit():
            row = self.get_by_id(owner_chat_id, int(key))
            if row is not None:
                return row
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT * FROM devices
                WHERE owner_chat_id = ?
                  AND (
                    IFNULL(serial, '') = ? COLLATE NOCASE
                    OR IFNULL(imei, '') = ? COLLATE NOCASE
                    OR IFNULL(phone, '') = ? COLLATE NOCASE
                  )
                ORDER BY id DESC
                LIMIT 1
                """,
                (owner_chat_id, key, key, key),
            ).fetchone()

    def delete_device(self, owner_chat_id: int, device_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM devices WHERE id = ? AND owner_chat_id = ?",
                (device_id, owner_chat_id),
            )
            return cur.rowcount > 0

    def count(self, owner_chat_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM devices WHERE owner_chat_id = ?",
                (owner_chat_id,),
            ).fetchone()
            return int(row["c"]) if row else 0

    def clear_all(self, owner_chat_id: int) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM devices WHERE owner_chat_id = ?",
                (owner_chat_id,),
            )
            return cur.rowcount

    def import_rows(self, owner_chat_id: int, rows: list[dict[str, Any]]) -> int:
        added = 0
        for row in rows:
            name = (
                row.get("name")
                or row.get("device")
                or row.get("device_name")
                or row.get("title")
            )
            if not name:
                continue
            self.add_device(
                owner_chat_id=owner_chat_id,
                name=str(name),
                model=_pick(row, "model", "device_model"),
                serial=_pick(row, "serial", "serial_number", "sn"),
                imei=_pick(row, "imei"),
                phone=_pick(row, "phone", "mobile", "number"),
                notes=_pick(row, "notes", "note", "remark"),
            )
            added += 1
        return added

    def import_csv_text(self, owner_chat_id: int, text: str) -> int:
        reader = csv.DictReader(text.splitlines())
        return self.import_rows(owner_chat_id, list(reader))

    def import_json_text(self, owner_chat_id: int, text: str) -> int:
        data = json.loads(text)
        if isinstance(data, dict):
            data = data.get("devices") or data.get("data") or [data]
        if not isinstance(data, list):
            raise ValueError("JSON mein devices ki list honi chahiye")
        return self.import_rows(owner_chat_id, data)

    def import_file(self, owner_chat_id: int, file_path: str | Path) -> int:
        path = Path(file_path)
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            return self.import_json_text(owner_chat_id, text)
        return self.import_csv_text(owner_chat_id, text)


def _pick(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return str(row[key])
        # case-insensitive fallback
        for existing, value in row.items():
            if existing.lower() == key.lower() and value not in (None, ""):
                return str(value)
    return None


def format_device(row: sqlite3.Row | dict[str, Any]) -> str:
    get = row.__getitem__ if not isinstance(row, dict) else row.get
    parts = [f"#{get('id')} • {get('name')}"]
    if get("model"):
        parts.append(f"Model: {get('model')}")
    if get("serial"):
        parts.append(f"Serial: {get('serial')}")
    if get("imei"):
        parts.append(f"IMEI: {get('imei')}")
    if get("phone"):
        parts.append(f"Phone: {get('phone')}")
    if get("notes"):
        parts.append(f"Notes: {get('notes')}")
    return "\n".join(parts)
