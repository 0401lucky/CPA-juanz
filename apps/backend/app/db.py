import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.metadata import build_display_name, extract_credential_identity
from app.security import generate_management_code, hash_management_code, verify_management_code


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS donors (
                    id TEXT PRIMARY KEY,
                    management_code_salt TEXT NOT NULL,
                    management_code_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS credential_records (
                    id TEXT PRIMARY KEY,
                    donor_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    cpa_file_name TEXT,
                    rejection_reason TEXT,
                    error_message TEXT,
                    payload_json TEXT,
                    parsed_email TEXT,
                    parsed_project_id TEXT,
                    duplicate_of TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(donor_id) REFERENCES donors(id)
                );

                CREATE TABLE IF NOT EXISTS oauth_flows (
                    id TEXT PRIMARY KEY,
                    state TEXT NOT NULL UNIQUE,
                    donor_id TEXT,
                    project_id TEXT NOT NULL,
                    baseline_files_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def create_donor(self) -> tuple[dict[str, Any], str]:
        donor_id = str(uuid.uuid4())
        management_code = generate_management_code()
        salt, digest = hash_management_code(management_code)
        timestamp = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO donors(id, management_code_salt, management_code_hash, created_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (donor_id, salt, digest, timestamp, timestamp)
            )
        return (
            {
                "id": donor_id,
                "created_at": timestamp,
                "last_seen_at": timestamp
            },
            management_code
        )

    def get_donor(self, donor_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM donors WHERE id = ?", (donor_id,)).fetchone()
        return dict(row) if row else None

    def touch_donor(self, donor_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE donors SET last_seen_at = ? WHERE id = ?",
                (utc_now(), donor_id)
            )

    def find_donor_by_management_code(self, management_code: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM donors").fetchall()
        for row in rows:
            data = dict(row)
            if verify_management_code(
                management_code,
                data["management_code_salt"],
                data["management_code_hash"]
            ):
                return data
        return None

    def _find_duplicate_record(
        self, parsed_email: str | None, parsed_project_id: str | None
    ) -> str | None:
        if not parsed_email or not parsed_project_id:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM credential_records
                WHERE parsed_email = ?
                  AND parsed_project_id = ?
                  AND status NOT IN ('deleted', 'rejected')
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (parsed_email, parsed_project_id)
            ).fetchone()
        return row["id"] if row else None

    def create_credential_record(
        self,
        *,
        donor_id: str,
        source_type: str,
        payload: dict[str, Any],
        fallback_name: str
    ) -> dict[str, Any]:
        record_id = str(uuid.uuid4())
        parsed_email, parsed_project_id = extract_credential_identity(payload)
        duplicate_of = self._find_duplicate_record(parsed_email, parsed_project_id)
        status = "duplicate_blocked" if duplicate_of else "pending_review"
        timestamp = utc_now()
        display_name = build_display_name(payload, fallback_name)
        payload_json = json.dumps(payload, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO credential_records(
                    id, donor_id, source_type, display_name, status, cpa_file_name,
                    rejection_reason, error_message, payload_json, parsed_email,
                    parsed_project_id, duplicate_of, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    donor_id,
                    source_type,
                    display_name,
                    status,
                    payload_json,
                    parsed_email,
                    parsed_project_id,
                    duplicate_of,
                    timestamp,
                    timestamp
                )
            )
        return self.get_credential(record_id)

    def list_credentials_for_donor(self, donor_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM credential_records
                WHERE donor_id = ?
                ORDER BY created_at DESC
                """,
                (donor_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def list_credentials(self, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM credential_records"
        params: tuple[Any, ...] = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY updated_at DESC, created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_credential(self, credential_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM credential_records WHERE id = ?",
                (credential_id,)
            ).fetchone()
        return dict(row) if row else None

    def update_credential(self, credential_id: str, **fields: Any) -> dict[str, Any] | None:
        if not fields:
            return self.get_credential(credential_id)
        fields["updated_at"] = utc_now()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        params = tuple(fields.values()) + (credential_id,)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE credential_records SET {assignments} WHERE id = ?",
                params
            )
        return self.get_credential(credential_id)

    def create_oauth_flow(
        self,
        *,
        state: str,
        donor_id: str | None,
        project_id: str,
        baseline_files: list[dict[str, Any]]
    ) -> dict[str, Any]:
        flow_id = str(uuid.uuid4())
        created_at = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO oauth_flows(id, state, donor_id, project_id, baseline_files_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    flow_id,
                    state,
                    donor_id,
                    project_id,
                    json.dumps(baseline_files, ensure_ascii=False),
                    created_at
                )
            )
        return self.get_oauth_flow(flow_id)

    def get_oauth_flow(self, flow_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM oauth_flows WHERE id = ?",
                (flow_id,)
            ).fetchone()
        return dict(row) if row else None

    def delete_oauth_flow(self, flow_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM oauth_flows WHERE id = ?", (flow_id,))

