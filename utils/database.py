import sqlite3
import uuid
from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "complaints.db"
STATUS_OPTIONS = ["Submitted", "Acknowledged", "In Progress", "Resolved"]
SLA_HOURS = {"low": 120, "medium": 48, "high": 24, "critical": 4}


def _connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS complaints (
            ticket_id TEXT PRIMARY KEY, category TEXT NOT NULL, severity TEXT NOT NULL,
            confidence REAL NOT NULL, description TEXT, latitude REAL NOT NULL, longitude REAL NOT NULL,
            department TEXT NOT NULL, routing_reason TEXT NOT NULL, recommended_action TEXT NOT NULL,
            priority_score INTEGER NOT NULL, priority_label TEXT NOT NULL, sla_hours INTEGER NOT NULL,
            provider TEXT, needs_review INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL, image_path TEXT, resolution_image_path TEXT,
            resolution_confidence REAL, citizen_feedback TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS complaint_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT NOT NULL, event TEXT NOT NULL,
            note TEXT, created_at TEXT NOT NULL
        )""")
        existing = {row[1] for row in conn.execute("PRAGMA table_info(complaints)")}
        migrations = {
            "priority_score": "INTEGER NOT NULL DEFAULT 50",
            "priority_label": "TEXT NOT NULL DEFAULT 'Medium'",
            "sla_hours": "INTEGER NOT NULL DEFAULT 48",
            "provider": "TEXT DEFAULT 'AI'",
            "needs_review": "INTEGER NOT NULL DEFAULT 0",
            "resolution_image_path": "TEXT",
            "resolution_confidence": "REAL",
            "citizen_feedback": "TEXT",
        }
        for name, definition in migrations.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE complaints ADD COLUMN {name} {definition}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def calculate_priority(severity: str, confidence: float, duplicate_count: int = 0) -> tuple[int, str]:
    base = {"low": 25, "medium": 50, "high": 75, "critical": 95}.get(severity, 50)
    score = min(100, round(base + (1 - confidence) * 5 + min(duplicate_count * 3, 15)))
    label = "Critical" if score >= 90 else "High" if score >= 70 else "Medium" if score >= 40 else "Low"
    return score, label


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return radius * 2 * asin(sqrt(a))


def find_possible_duplicates(category: str, latitude: float, longitude: float, radius_km: float = 0.35) -> list[dict]:
    matches = []
    for row in get_complaints():
        if row["category"] == category and row["status"] != "Resolved" and _distance_km(latitude, longitude, row["latitude"], row["longitude"]) <= radius_km:
            matches.append(row)
    return matches


def create_complaint(**fields) -> dict:
    init_db()
    duplicates = find_possible_duplicates(fields["category"], fields["latitude"], fields["longitude"])
    priority_score, priority_label = calculate_priority(fields["severity"], fields["confidence"], len(duplicates))
    now = _now()
    ticket_id = f"CIV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    fields.update(ticket_id=ticket_id, priority_score=priority_score, priority_label=priority_label, sla_hours=SLA_HOURS.get(fields["severity"], 48), provider=fields.get("provider", "AI"), needs_review=int(fields.get("needs_review", False)), status="Submitted", resolution_image_path=None, resolution_confidence=None, citizen_feedback=None, created_at=now, updated_at=now)
    keys = list(fields)
    with _connect() as conn:
        conn.execute(f"INSERT INTO complaints ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})", [fields[k] for k in keys])
        conn.execute("INSERT INTO complaint_events (ticket_id,event,note,created_at) VALUES (?,?,?,?)", (ticket_id, "Complaint submitted", f"AI routed to {fields['department']}", now))
    complaint = get_complaint(ticket_id)
    complaint["duplicate_matches"] = duplicates
    return complaint


def get_complaints() -> list[dict]:
    init_db()
    with _connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM complaints ORDER BY created_at DESC")]


def get_complaint(ticket_id: str) -> dict:
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM complaints WHERE ticket_id = ?", (ticket_id,)).fetchone()
    return dict(row) if row else {}


def get_events(ticket_id: str) -> list[dict]:
    init_db()
    with _connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM complaint_events WHERE ticket_id=? ORDER BY created_at", (ticket_id,))]


def update_status(ticket_id: str, status: str, note: str = "") -> None:
    if status not in STATUS_OPTIONS:
        raise ValueError("Invalid complaint status.")
    now = _now()
    with _connect() as conn:
        conn.execute("UPDATE complaints SET status=?, updated_at=? WHERE ticket_id=?", (status, now, ticket_id))
        conn.execute("INSERT INTO complaint_events (ticket_id,event,note,created_at) VALUES (?,?,?,?)", (ticket_id, f"Status changed to {status}", note, now))


def save_resolution(ticket_id: str, image_path: str, confidence: float) -> None:
    now = _now()
    with _connect() as conn:
        conn.execute("UPDATE complaints SET resolution_image_path=?, resolution_confidence=?, updated_at=? WHERE ticket_id=?", (image_path, confidence, now, ticket_id))
        conn.execute("INSERT INTO complaint_events (ticket_id,event,note,created_at) VALUES (?,?,?,?)", (ticket_id, "Resolution evidence uploaded", f"AI verification confidence: {confidence:.0%}", now))


def save_feedback(ticket_id: str, feedback: str) -> None:
    now = _now()
    status = "Resolved" if feedback == "Resolved" else "In Progress"
    with _connect() as conn:
        conn.execute("UPDATE complaints SET citizen_feedback=?, status=?, updated_at=? WHERE ticket_id=?", (feedback, status, now, ticket_id))
        conn.execute("INSERT INTO complaint_events (ticket_id,event,note,created_at) VALUES (?,?,?,?)", (ticket_id, f"Citizen feedback: {feedback}", "Complaint reopened if not resolved", now))


init_db()
