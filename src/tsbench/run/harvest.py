"""Images a run produced: copied next to its transcript (`<task>-k<i>.artifacts/`) with their sha256."""
from __future__ import annotations

import hashlib
import os
import pathlib
import stat as stat_mod

ARTIFACT_SUFFIXES = (".png", ".svg")
ARTIFACT_MAX_BYTES = 10 * 1024 * 1024
ARTIFACT_MAX_FILES = 20


def artifacts_dir_of(transcript: pathlib.Path) -> pathlib.Path:
    """`<run stem>.artifacts/` next to the transcript."""
    return transcript.with_name(transcript.name[: -len(".jsonl")] + ".artifacts")


def harvest_artifacts(cwd, dest) -> list[dict]:
    """Copy the *.png / *.svg files in the top level of `cwd` into `dest` and return [{name, sha256}] (sha256 of the
    bytes copied, recomputed here). Symlinks and anything that is not a regular file are skipped and never followed
    (lstat, then O_NOFOLLOW); files above ARTIFACT_MAX_BYTES are skipped; at most ARTIFACT_MAX_FILES are taken. An
    OSError on one file skips that file: harvesting never fails a run. `dest` is created only if there is a file."""
    found: list[dict] = []
    try:
        names = sorted(p.name for p in pathlib.Path(cwd).iterdir())
    except OSError:
        return found
    for name in names:
        if len(found) >= ARTIFACT_MAX_FILES:
            break
        if not name.lower().endswith(ARTIFACT_SUFFIXES) or name.startswith("."):
            continue
        path = pathlib.Path(cwd) / name
        try:
            st = os.lstat(path)
            if not stat_mod.S_ISREG(st.st_mode) or st.st_size > ARTIFACT_MAX_BYTES:
                continue
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
            with os.fdopen(fd, "rb") as fh:
                data = fh.read(ARTIFACT_MAX_BYTES + 1)
            if len(data) > ARTIFACT_MAX_BYTES:
                continue
            dest = pathlib.Path(dest)
            dest.mkdir(parents=True, exist_ok=True)
            (dest / name).write_bytes(data)
        except OSError:
            continue
        found.append({"name": name, "sha256": hashlib.sha256(data).hexdigest()})
    return found


def image_sha_match(structured_output, artifacts: list[dict]) -> bool | None:
    """None if the answer reports no `image_sha256`; else whether it equals the sha256 of a harvested file."""
    sha = structured_output.get("image_sha256") if isinstance(structured_output, dict) else None
    if not isinstance(sha, str) or not sha.strip():
        return None
    return sha.strip().lower() in {a["sha256"] for a in artifacts}
