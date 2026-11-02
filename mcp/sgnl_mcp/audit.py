"""Append-only JSONL audit log of Write and Workflow operations, with secrets removed."""
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SECRET_KEYS = {
    "client_secret", "clientsecret", "token", "authorization", "jwt",
    "signed_url", "signedurl", "password", "confirmation_token",
}
# Pre-signed S3 query parameters: whoever has the URL can download or upload until it expires.
_SIGNED_QUERY = re.compile(r"(https?://[^\s\"?]+)\?[^\s\"]*(X-Amz-|Signature=|signature=)[^\s\"]*")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("[redacted]" if k.lower() in SECRET_KEYS else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return _SIGNED_QUERY.sub(r"\1?[redacted]", value)
    return value


class AuditLog:
    def __init__(self, path: Path, rotate_bytes: int = 10 * 1024 * 1024):
        self.path = Path(path)
        self.rotate_bytes = rotate_bytes
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: dict) -> None:
        record = {"ts": datetime.now(timezone.utc).isoformat(), **redact(event)}
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            if self.path.exists() and self.path.stat().st_size > self.rotate_bytes:
                self.path.replace(self.path.with_suffix(self.path.suffix + ".1"))
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
