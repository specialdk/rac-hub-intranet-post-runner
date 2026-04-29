"""intranet-post runner — entry point.

One run = one invocation. The script:
  1. Loads env vars and reference files (reference loading happens at import time)
  2. Calls GET /skill/pending
  3. For each pending submission, decides: process or quarantine
  4. Logs run summary and exits

Designed to be called by Windows Task Scheduler hourly during work hours,
but invoking by hand (`python intranet_post.py`) does the same thing.

Environment variables (loaded from .env):
  ANTHROPIC_API_KEY        — Anthropic API key (required)
  BACKEND_URL              — backend base URL (defaults to Railway prod URL via .env.example)
  SKILL_NOTIFY_SECRET      — shared secret matching the backend's env var (required)

Optional:
  CLAUDE_MODEL             — defaults to claude-opus-4-7
  CLAUDE_MAX_TOKENS        — defaults to 4096
  LOG_DIR                  — defaults to ./logs
  STATE_FILE               — defaults to ./state.json
"""

from __future__ import annotations

import sys
from typing import Any

from dotenv import load_dotenv

import backend_client
import claude_client
import log
import state


# ---------------------------------------------------------------------------
# AdminNote composer — pure logic
# ---------------------------------------------------------------------------

def compose_admin_note(
    *,
    cleaning: claude_client.CleanedText,
    title_generated: bool,
    highlight_generated: bool,
) -> str:
    """Build the AdminNote string per SKILL.md §2e.

    Examples:
      'Auto-cleaned: 3 fillers, 1 swear removed. Title generated.'
      'Auto-cleaned: 2 fillers removed. Submitter\\'s title and highlight used verbatim.'
      'Submitter\\'s text used verbatim. Title and highlight generated.'
      'Submitter\\'s text, title and highlight used verbatim.'
    """
    parts: list[str] = []

    if cleaning.verbatim:
        # No edits at all
        if title_generated and highlight_generated:
            parts.append("Submitter's text used verbatim. Title and highlight generated.")
        elif title_generated:
            parts.append("Submitter's text and highlight used verbatim. Title generated.")
        elif highlight_generated:
            parts.append("Submitter's text and title used verbatim. Highlight generated.")
        else:
            parts.append("Submitter's text, title and highlight used verbatim.")
    else:
        # Build separate phrases per action verb (removed / fixed / added).
        # "Auto-cleaned: 3 fillers, 1 swear removed; 1 stutter fixed; 2 paragraph
        # breaks added." reads naturally; mixing them under one verb does not.
        def _plural(n: int, word: str) -> str:
            return f"{n} {word}{'' if n == 1 else 's'}"

        removed_bits: list[str] = []
        if cleaning.fillers_removed:
            removed_bits.append(_plural(cleaning.fillers_removed, "filler"))
        if cleaning.swears_removed:
            removed_bits.append(_plural(cleaning.swears_removed, "swear"))

        action_phrases: list[str] = []
        if removed_bits:
            action_phrases.append(f"{', '.join(removed_bits)} removed")
        if cleaning.stutters_fixed:
            action_phrases.append(f"{_plural(cleaning.stutters_fixed, 'stutter')} fixed")
        if cleaning.paragraph_breaks_added:
            action_phrases.append(
                f"{_plural(cleaning.paragraph_breaks_added, 'paragraph break')} added"
            )

        if action_phrases:
            parts.append(f"Auto-cleaned: {'; '.join(action_phrases)}.")
        else:
            # cleaned_text differs from input but no counters set — defensive
            parts.append("Auto-cleaned.")

        if title_generated and highlight_generated:
            parts.append("Title and highlight generated.")
        elif title_generated:
            parts.append("Title generated.")
        elif highlight_generated:
            parts.append("Highlight generated.")
        else:
            parts.append("Submitter's title and highlight used verbatim.")

    if cleaning.has_enumerated_list:
        parts.append("Note: body contains an enumerated list that could be bulleted on review.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Per-submission flow
# ---------------------------------------------------------------------------

def _process_one(item: dict[str, Any]) -> str:
    """Process one entry from /skill/pending. Returns one of:
      'succeeded'   — full happy path
      'quarantined' — permanent failure, folder moved
      'skipped'     — transient failure, folder left in place

    Internally this also handles the quarantine call when a /skill/pending
    entry already arrived with an `error` field (malformed submission.json).
    """
    folder_id = item["folder_id"]
    folder_name = item.get("folder_name", folder_id)

    # --- Pre-flight: malformed submission.json detected by backend
    if item.get("error"):
        reason = f"{item['error']}: {item.get('message', '')}".strip(": ")
        try:
            backend_client.quarantine(folder_id=folder_id, error_text=reason)
            log.quarantined(folder_name, reason)
            state.reset_failure(folder_id)
            return "quarantined"
        except backend_client.TransientBackendError as e:
            log.skipped_transient(folder_name, str(e))
            state.increment_failure(folder_id)
            return "skipped"
        except backend_client.BackendError as e:
            log.error(f"failed to quarantine {folder_name}: {e}")
            return "skipped"

    sub = item["submission"]

    # --- Step 2b: clean the body text
    try:
        cleaning = claude_client.clean_text(sub["text"])
    except Exception as e:
        # Anthropic API failure — usually transient (rate limit, network)
        log.skipped_transient(folder_name, f"Anthropic API error during cleaning: {e}")
        state.increment_failure(folder_id)
        return "skipped"

    # --- Step 2c/2d: title and highlight (resolved or generated)
    title_was_blank = not (sub.get("title_suggestion") or "").strip()
    highlight_was_blank = not (sub.get("highlight_suggestion") or "").strip()

    if title_was_blank:
        try:
            resolved_title = claude_client.generate_title(cleaning.cleaned_text).title
        except Exception as e:
            log.skipped_transient(folder_name, f"Anthropic API error during title gen: {e}")
            state.increment_failure(folder_id)
            return "skipped"
    else:
        resolved_title = sub["title_suggestion"]

    if highlight_was_blank:
        try:
            resolved_highlight = claude_client.generate_highlight(
                cleaning.cleaned_text, resolved_title
            ).highlight
        except Exception as e:
            log.skipped_transient(folder_name, f"Anthropic API error during highlight gen: {e}")
            state.increment_failure(folder_id)
            return "skipped"
    else:
        resolved_highlight = sub["highlight_suggestion"]

    # --- Step 2e: compose AdminNote
    admin_note = compose_admin_note(
        cleaning=cleaning,
        title_generated=title_was_blank,
        highlight_generated=highlight_was_blank,
    )

    # --- Step 2f: hand off to backend
    try:
        result = backend_client.process(
            folder_id=folder_id,
            cleaned_text=cleaning.cleaned_text,
            resolved_title=resolved_title,
            resolved_highlight=resolved_highlight,
            admin_note=admin_note,
        )
    except backend_client.PermanentBackendError as e:
        # Validation reject, schema mismatch — quarantine
        try:
            backend_client.quarantine(
                folder_id=folder_id,
                error_text=f"/skill/process returned {e.code}: {e.message}",
            )
            log.quarantined(folder_name, f"{e.code}: {e.message}")
            state.reset_failure(folder_id)
            return "quarantined"
        except backend_client.BackendError as q:
            log.error(f"failed to quarantine {folder_name} after process error: {q}")
            return "skipped"
    except backend_client.TransientBackendError as e:
        log.skipped_transient(folder_name, str(e))
        state.increment_failure(folder_id)
        return "skipped"

    # --- Step 2g: notify admin (success path)
    destination = result["destination"]
    row_number = result["row_number"]
    submitted_by = sub.get("submitter_name", "")
    try:
        backend_client.notify_admin(
            destination=destination,
            row_number=row_number,
            title=resolved_title,
            submitted_by=submitted_by,
        )
    except backend_client.BackendError as e:
        # Email failure is non-fatal — submission is in the sheet, admin can
        # find it via the PWA's Pending Review queue. Log loudly so we notice.
        log.warning(
            f"/admin/notify failed for {folder_name} (row {row_number}): {e}. "
            "Submission landed in the sheet OK."
        )

    log.processed(folder_name, destination, row_number, resolved_title, admin_note)
    state.reset_failure(folder_id)
    return "succeeded"


# ---------------------------------------------------------------------------
# Run loop
# ---------------------------------------------------------------------------

def run() -> int:
    """One full run. Returns process exit code (0 success, 1 fatal config error)."""
    # override=True: the .env file is the source of truth. Without this, an
    # empty ANTHROPIC_API_KEY already in the shell environment (Windows
    # often has these set globally) would silently shadow the file's value.
    load_dotenv(override=True)
    log.run_start()

    # --- Step 1: discover pending submissions
    try:
        pending = backend_client.get_pending()
    except backend_client.AuthBackendError as e:
        log.error(str(e))
        return 1
    except backend_client.TransientBackendError as e:
        # Backend unreachable — log and exit; nothing to retry until next run
        log.skipped_transient("(run)", str(e))
        log.run_end(processed=0, succeeded=0, quarantined=0, skipped=0)
        return 0
    except backend_client.PermanentBackendError as e:
        log.error(f"/skill/pending returned a permanent error: {e}")
        return 1

    if not pending:
        log.no_pending()
        log.run_end(processed=0, succeeded=0, quarantined=0, skipped=0)
        # Still prune state — the active folder list is empty
        state.prune([])
        return 0

    # Surface the warning for any folder that's been failing transiently for
    # a long time. (The skill never auto-quarantines on transient errors —
    # that's an admin call.)
    threshold = state.transient_warning_threshold()
    for item in pending:
        fid = item["folder_id"]
        count = state.get_failure_count(fid)
        if count >= threshold:
            log.warning(
                f"folder {item.get('folder_name', fid)} has failed transiently "
                f"{count} consecutive runs — investigate"
            )

    # --- Step 2: process each
    succeeded = quarantined = skipped = 0
    for item in pending:
        outcome = _process_one(item)
        if outcome == "succeeded":
            succeeded += 1
        elif outcome == "quarantined":
            quarantined += 1
        elif outcome == "skipped":
            skipped += 1

    # --- Cleanup: drop state entries for folders no longer in Submissions/
    state.prune([item["folder_id"] for item in pending])

    # --- Step 3: run summary
    total = succeeded + quarantined + skipped
    log.run_end(processed=total, succeeded=succeeded, quarantined=quarantined, skipped=skipped)
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
