"""Durable, identity-bound records for new prepared-prompt experiments."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from dataset_contract import stable_hash


class JournalError(RuntimeError):
    """Persistence failure must abort, never trigger another paid request."""


def now():
    return datetime.now(timezone.utc).isoformat()


def record_key(item):
    return stable_hash([item["id"], item["arm"], item["condition"]])


@contextmanager
def run_lock(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ".execution.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise JournalError("Run is locked; inspect concurrent/interrupted execution before reuse") from exc
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        yield
    finally:
        if path.exists():
            path.unlink()


def read_jsonl(path):
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                raise JournalError(f"Blank/corrupt journal line {line_number}; recovery requires inspection")
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise JournalError(f"Corrupt journal line {line_number}; no silent skipping") from exc
    return records


class RunJournal:
    def __init__(self, folder, identity):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.identity_hash = stable_hash(identity)
        manifest_path = self.folder / "manifest.json"
        expected = {"schema_version": 2, "identity_hash": self.identity_hash, "identity": identity}
        if manifest_path.exists():
            saved = json.loads(manifest_path.read_text(encoding="utf-8"))
            if saved != expected:
                raise JournalError("Run identity mismatch: dataset/split/model/prompt/retrieval/config changed")
        else:
            if any(p.name != ".execution.lock" for p in self.folder.iterdir()):
                raise JournalError("Nonempty run directory has no valid manifest")
            with manifest_path.open("x", encoding="utf-8") as stream:
                json.dump(expected, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
        self.records_path = self.folder / "records.jsonl"
        self.events_path = self.folder / "events.jsonl"
        self.records = {}
        for row in read_jsonl(self.records_path):
            key = record_key(row)
            if row.get("run_identity_hash") != self.identity_hash or key in self.records:
                raise JournalError("Duplicate record or wrong run identity")
            self.records[key] = row
        starts = set()
        for event in read_jsonl(self.events_path):
            if event.get("run_identity_hash") != self.identity_hash:
                raise JournalError("Event identity mismatch")
            starts.add(event["record_key"])
        pending = starts - self.records.keys()
        if pending:
            raise JournalError("Unfinished request(s) found; inspect saved attempts before retrying to avoid untracked duplicate calls")

    def _append(self, path, record):
        try:
            serialized = json.dumps(record, ensure_ascii=False, allow_nan=False)
            with path.open("a", encoding="utf-8") as stream:
                stream.write(serialized + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        except (OSError, TypeError, ValueError) as exc:
            raise JournalError("Cannot persist journal; stop inference before any further request") from exc

    def event(self, item, attempt, event):
        self._append(self.events_path, {**event, "record_key": record_key(item), "attempt": attempt,
                                       "run_identity_hash": self.identity_hash, "time_utc": now()})

    def save(self, record):
        key = record_key(record)
        if key in self.records:
            raise JournalError("Cannot overwrite a completed condition")
        row = {**record, "schema_version": 2, "run_identity_hash": self.identity_hash}
        self._append(self.records_path, row)
        self.records[key] = row
        return row


def verify_pinned_inputs(root, inputs):
    root = Path(root).resolve()
    for pinned in inputs:
        path = (root / pinned["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Pinned input missing/outside workspace")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != pinned["sha256"]:
            raise ValueError("Pinned input hash mismatch: " + pinned["path"])
