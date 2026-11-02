"""PROV-JSON export and the hash-chain check over trace records (see `tsbench.core.trace`).

A record is the JSON that one traced process wrote. This module reads records, names their inputs and outputs by
sha256, builds a PROV-JSON document and checks that every file a process read is the version an earlier process wrote.
It uses the standard library only and never touches file contents: it works on the hashes the tracer recorded.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PREFIX = {"prov": "http://www.w3.org/ns/prov#", "tsbench": "https://tsbench.invalid/prov#", "ex": "urn:tsbench:"}
_WRITE_FLAGS = frozenset("wax+")


def _is_write_mode(mode: str | None) -> bool:
    return bool(mode) and bool(_WRITE_FLAGS & set(mode or ""))


def load_records(trace_root: str | Path) -> list[dict[str, Any]]:
    """Read `<trace_root>/<step>/*.trace.json`. Adds `step`, skips files that are not valid JSON, sorts by start."""
    root = Path(trace_root)
    records: list[dict[str, Any]] = []
    if not root.is_dir():
        return records
    for path in sorted(root.rglob("*.trace.json")):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        data["step"] = path.relative_to(root).parts[0]
        records.append(data)
    records.sort(key=lambda r: _num(r.get("start")))
    return records


def _num(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def inputs(record: dict[str, Any]) -> dict[str, str]:
    """Paths the process read (open in a read-only mode) with their sha256 at read. The first read of a path wins."""
    found: dict[str, str] = {}
    for event in record.get("files") or []:
        if event.get("event") != "open" or _is_write_mode(event.get("mode")):
            continue
        sha = event.get("sha256_at_read")
        if sha and event.get("path") not in found:
            found[event["path"]] = sha
    return found


def outputs(record: dict[str, Any]) -> dict[str, str]:
    """Paths the process wrote (open in a write mode, or a rename target) with their sha256 at process end.

    A file that is gone at the end (a renamed .tmp file) has no hash and is left out."""
    found: dict[str, str] = {}
    for event in record.get("files") or []:
        kind = event.get("event")
        if kind == "open" and _is_write_mode(event.get("mode")):
            path = event.get("path")
        elif kind == "rename":
            path = event.get("target")
        else:
            continue
        sha = event.get("sha256_at_end")
        if path and sha:
            found[path] = sha
    return found


def activity_id(record: dict[str, Any]) -> str:
    """Stable id of one process record: step, pid and start time."""
    return f"ex:activity/{record.get('step', '')}/{record.get('pid')}/{_num(record.get('start')):.6f}"


def _entity_id(path: str, sha: str) -> str:
    return "ex:entity/" + hashlib.sha256(f"{path}\0{sha}".encode()).hexdigest()[:24]


def _iso(epoch: Any) -> str:
    return datetime.fromtimestamp(_num(epoch), tz=UTC).isoformat()


def to_prov(records: list[dict[str, Any]]) -> dict[str, Any]:
    """PROV-JSON: one activity per record, one entity per (path, sha256), `used` and `wasGeneratedBy` relations."""
    entity: dict[str, dict[str, str]] = {}
    activity: dict[str, dict[str, str]] = {}
    used: dict[str, dict[str, str]] = {}
    generated: dict[str, dict[str, str]] = {}
    for record in records:
        act = activity_id(record)
        activity[act] = {"prov:startTime": _iso(record.get("start")), "prov:endTime": _iso(record.get("end")),
                         "tsbench:command": str(record.get("command", "")),
                         "tsbench:step": str(record.get("step", ""))}
        for path, sha in inputs(record).items():
            ent = _entity_id(path, sha)
            entity[ent] = {"tsbench:path": path, "tsbench:sha256": sha}
            used[f"ex:used/{act}/{ent}"] = {"prov:activity": act, "prov:entity": ent}
        for path, sha in outputs(record).items():
            ent = _entity_id(path, sha)
            entity[ent] = {"tsbench:path": path, "tsbench:sha256": sha}
            generated[f"ex:gen/{act}/{ent}"] = {"prov:activity": act, "prov:entity": ent}
    return {"prefix": dict(PREFIX), "entity": entity, "activity": activity, "used": used,
            "wasGeneratedBy": generated}


def hash_chain(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Breaks in the chain of file versions.

    For each input of each record the producers are the other records that ended at or before the reader started and
    have the path among their outputs. The one that ended last wins. A break is an input whose hash differs from that
    producer's hash. An input without a producer is no break."""
    prepared = [(record, activity_id(record), outputs(record)) for record in records]
    breaks: list[dict[str, str]] = []
    for reader, reader_id, _ in prepared:
        started = _num(reader.get("start"))
        for path, found in inputs(reader).items():
            best: tuple[tuple[float, float], str, str] | None = None
            for producer, producer_id, produced in prepared:
                if producer_id == reader_id or path not in produced or _num(producer.get("end")) > started:
                    continue
                order = (_num(producer.get("end")), _num(producer.get("start")))
                if best is None or order >= best[0]:
                    best = (order, producer_id, produced[path])
            if best is not None and best[2] != found:
                breaks.append({"path": path, "expected": best[2], "found": found, "producer": best[1],
                               "consumer": reader_id})
    return breaks
