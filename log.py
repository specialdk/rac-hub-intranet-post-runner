"""Plain-text daily log writer for the runner.

One file per local-time day under LOG_DIR. Append-only. Each line starts with
an ISO timestamp followed by the event text. The skill spec calls for a few
specific log line shapes — keep them readable; optimise for "what happened
today?" grep, not machine parsing.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path


def _log_dir() -> Path:
    return Path(os.environ.get("LOG_DIR", "./logs")).resolve()


def _today_path() -> Path:
    d = _log_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{datetime.now().strftime('%Y-%m-%d')}.log"


def _now_iso() -> str:
    # Local time with timezone offset, to-the-second. Matches the contract's
    # submitted_at shape exactly so admins can correlate by timestamp.
    return datetime.now().astimezone().isoformat(timespec="seconds")


def append(line: str) -> None:
    """Append a single log line, prefixed with the current ISO timestamp."""
    path = _today_path()
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{_now_iso()}: {line}\n")


# Convenience wrappers matching the SKILL.md log line shapes ----------------

def run_start() -> None:
    append("run started")


def run_end(processed: int, succeeded: int, quarantined: int, skipped: int) -> None:
    append(
        f"run complete. Processed: {processed}, Succeeded: {succeeded}, "
        f"Quarantined: {quarantined}, Skipped (transient): {skipped}."
    )


def no_pending() -> None:
    append("no pending submissions")


def processed(folder_name: str, destination: str, row_number: int, title: str, admin_note: str) -> None:
    append(
        f'processed {folder_name} -> {destination} row {row_number}. '
        f'Title: "{title}". {admin_note}'
    )


def quarantined(folder_name: str, reason: str) -> None:
    append(f"quarantined {folder_name}. Reason: {reason}")


def skipped_transient(folder_name: str, reason: str) -> None:
    append(
        f"skipped {folder_name} due to transient backend error: {reason}. "
        "Will retry on next run."
    )


def warning(message: str) -> None:
    append(f"WARNING: {message}")


def error(message: str) -> None:
    append(f"ERROR: {message}")
