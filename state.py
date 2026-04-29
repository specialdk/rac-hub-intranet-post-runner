"""Persistent transient-failure counter, keyed by folder_id.

Per SKILL.md edge cases: 'after 5 consecutive failed runs on the same folder,
log a warning so the admin can investigate.' We persist counts in a small
JSON file so the count survives across runs (Task Scheduler invocations are
separate processes).

Successful processing or quarantining clears the entry. After each run the
state is pruned to only contain folder_ids that are still in the pending
list — orphans (folders moved out of Submissions) are forgotten.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


_TRANSIENT_WARNING_THRESHOLD = 5


def _state_path() -> Path:
    return Path(os.environ.get("STATE_FILE", "./state.json")).resolve()


def _load() -> dict[str, int]:
    p = _state_path()
    if not p.exists():
        return {}
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Defensive: tolerate manual edits
        if not isinstance(data, dict):
            return {}
        return {str(k): int(v) for k, v in data.items() if isinstance(v, (int, float))}
    except (json.JSONDecodeError, ValueError, OSError):
        return {}


def _save(state: dict[str, int]) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    # Sort keys for deterministic file output — easier to diff manually
    with p.open("w", encoding="utf-8") as f:
        json.dump(state, f, sort_keys=True, indent=2)
        f.write("\n")


def get_failure_count(folder_id: str) -> int:
    return _load().get(folder_id, 0)


def increment_failure(folder_id: str) -> int:
    """Increment and persist the failure count. Returns the new value."""
    s = _load()
    new = s.get(folder_id, 0) + 1
    s[folder_id] = new
    _save(s)
    return new


def reset_failure(folder_id: str) -> None:
    """Drop the failure entry on success or quarantine."""
    s = _load()
    if folder_id in s:
        del s[folder_id]
        _save(s)


def prune(active_folder_ids: list[str]) -> None:
    """Remove failure entries for folders that no longer appear in pending.

    Folders disappear from Submissions/ when they move to Processed/ or
    Quarantine/. Their counters are no longer meaningful and would otherwise
    accumulate forever.
    """
    s = _load()
    active = set(active_folder_ids)
    pruned = {fid: count for fid, count in s.items() if fid in active}
    if pruned != s:
        _save(pruned)


def transient_warning_threshold() -> int:
    return _TRANSIENT_WARNING_THRESHOLD
