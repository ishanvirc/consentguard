"""Consent Ledger — SQLite store of consent evidence + append-only audit log.

Shared by BOTH surfaces:
  * mcp_server/consent_ledger.py  → exposes these functions as MCP tools
  * app/agent.py                  → in-process tool fallback for the ADK agents

PRIVACY BY ARCHITECTURE: agents only ever receive `contact_id` + consent facts.
Raw email/phone stays inside this module's tables and is joined back to a
message only AFTER the gate passes — so no PII transits an LLM context window.

Usage:
    uv run python -m app.ledger seed   # create + seed the demo database
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.gate import ConsentBasis, ConsentEvidence

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("CONSENTGUARD_DB_PATH", REPO_ROOT / "data" / "consent_ledger.db"))
AUDIT_LOG = Path(os.environ.get("CONSENTGUARD_AUDIT_LOG", REPO_ROOT / "data" / "audit_log.jsonl"))
SEED_FILE = REPO_ROOT / "data" / "seed_contacts.json"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    contact_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,        -- first name only; demo data is fictional
    email TEXT,                        -- PII: never returned to agents
    phone TEXT                         -- PII: never returned to agents
);
CREATE TABLE IF NOT EXISTS consent_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT NOT NULL REFERENCES contacts(contact_id),
    channel TEXT NOT NULL,             -- consent is channel-specific (CASL)
    basis TEXT NOT NULL,               -- express | implied_purchase | implied_inquiry | withdrawn
    granted_at TEXT NOT NULL,          -- ISO-8601 UTC
    source TEXT NOT NULL,              -- provenance, e.g. web_form_v3
    wording TEXT NOT NULL              -- exact opt-in language (CASL record-keeping)
);
"""


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def seed() -> int:
    """(Re)create the demo database from data/seed_contacts.json."""
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    with _conn() as conn:
        conn.execute("DELETE FROM consent_events")
        conn.execute("DELETE FROM contacts")
        for c in data["contacts"]:
            conn.execute(
                "INSERT INTO contacts VALUES (?,?,?,?)",
                (c["contact_id"], c["display_name"], c.get("email"), c.get("phone")),
            )
            for e in c.get("consent_events", []):
                conn.execute(
                    "INSERT INTO consent_events (contact_id, channel, basis, granted_at, source, wording)"
                    " VALUES (?,?,?,?,?,?)",
                    (c["contact_id"], e["channel"], e["basis"], e["granted_at"],
                     e["source"], e["wording"]),
                )
    return len(data["contacts"])


def get_consent(contact_id: str, channel: str) -> ConsentEvidence:
    """LATEST consent record for contact × channel. No record → fail-closed NONE.

    'Latest wins' matters: a 2026 renewed express consent supersedes a 2025
    withdrawal. The adversarial verifier uses get_consent_history() to check
    exactly this when adjudicating auditor flags.
    """
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM consent_events WHERE contact_id=? AND channel=?"
            " ORDER BY granted_at DESC LIMIT 1",
            (contact_id, channel),
        ).fetchone()
    if row is None:
        return ConsentEvidence(contact_id, channel, ConsentBasis.NONE, None)
    return ConsentEvidence(
        contact_id=contact_id,
        channel=row["channel"],
        basis=ConsentBasis(row["basis"]),
        granted_at=datetime.fromisoformat(row["granted_at"]),
        source=row["source"],
        wording=row["wording"],
    )


def get_consent_history(contact_id: str) -> list[dict]:
    """Full consent trail across ALL channels — the verifier's evidence base."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT channel, basis, granted_at, source, wording FROM consent_events"
            " WHERE contact_id=? ORDER BY granted_at ASC",
            (contact_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def record_unsubscribe(contact_id: str, channel: str) -> dict:
    """Log a withdrawal. CASL: honor within 10 business days; we honor instantly."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO consent_events (contact_id, channel, basis, granted_at, source, wording)"
            " VALUES (?,?,?,?,?,?)",
            (contact_id, channel, ConsentBasis.WITHDRAWN.value, now,
             "unsubscribe_link", "user clicked unsubscribe"),
        )
    append_audit({"event": "unsubscribe", "contact_id": contact_id, "channel": channel, "at": now})
    return {"contact_id": contact_id, "channel": channel, "withdrawn_at": now}


def append_audit(entry: dict) -> None:
    """Append-only JSONL audit log. Pseudonymous IDs only — no PII."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry.setdefault("logged_at", datetime.now(timezone.utc).isoformat())
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def get_audit_trail(limit: int = 50) -> list[dict]:
    if not AUDIT_LOG.exists():
        return []
    lines = AUDIT_LOG.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines[-limit:]]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        n = seed()
        print(f"Seeded {n} fictional contacts into {DB_PATH}")
    else:
        print("Usage: python -m app.ledger seed")
