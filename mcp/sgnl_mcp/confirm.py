"""Two-phase confirmation of Write and Workflow operations, and the idempotency journal.

Phase 1 stores a preview and issues a single-use token bound to the tool, its normalized
arguments and a snapshot of the objects it will change. Phase 2 must present the same token
with the same arguments; the service then re-reads the objects and refuses if the snapshot
changed. The token proves that what runs is exactly what was shown; that a human agreed is
proven by the client's permission prompt (Write) or by elicitation (Workflow).
"""
import hashlib
import json
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .errors import ToolFailure


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()


@dataclass
class Pending:
    tool: str
    args_hash: str
    snapshot: Any
    preview: Any
    expires_at: float


class ConfirmationStore:
    def __init__(self, ttl_sec: int, journal_path: Path):
        self.ttl_sec = ttl_sec
        self._pending: dict[str, Pending] = {}
        self._lock = threading.Lock()
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(journal_path), check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS completed (token_hash TEXT PRIMARY KEY, tool TEXT, result TEXT, ts REAL)"
        )
        self._db.execute("DELETE FROM completed WHERE ts < ?", (time.time() - 24 * 3600,))
        self._db.commit()

    def issue(self, tool: str, args: dict, snapshot: Any, preview: Any) -> str:
        token = secrets.token_urlsafe(24)
        with self._lock:
            now = time.time()
            self._pending = {k: v for k, v in self._pending.items() if v.expires_at > now}
            self._pending[token] = Pending(tool, fingerprint(args), snapshot, preview, now + self.ttl_sec)
        return token

    def peek(self, token: str, tool: str) -> Optional[Pending]:
        with self._lock:
            pending = self._pending.get(token)
        if pending is None or pending.tool != tool or pending.expires_at < time.time():
            return None
        return pending

    def take(self, token: str, tool: str, args: dict) -> Pending:
        """Consumes the token. Raises CONFIRMATION_INVALID if it is unknown, expired, or for other arguments."""
        with self._lock:
            pending = self._pending.pop(token, None)
        if pending is None or pending.tool != tool:
            raise ToolFailure("CONFIRMATION_INVALID", "Unknown or already used confirmation token; request a new preview")
        if pending.expires_at < time.time():
            raise ToolFailure("CONFIRMATION_INVALID", "Confirmation token expired; request a new preview")
        if pending.args_hash != fingerprint(args):
            raise ToolFailure("CONFIRMATION_INVALID", "Arguments differ from the confirmed preview; request a new preview")
        return pending

    def completed(self, token: str) -> Optional[Any]:
        row = self._db.execute(
            "SELECT result FROM completed WHERE token_hash = ?", (fingerprint(token),)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def record(self, token: str, tool: str, result: Any) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO completed VALUES (?, ?, ?, ?)",
                (fingerprint(token), tool, json.dumps(result, default=str, ensure_ascii=False), time.time()),
            )
            self._db.commit()
