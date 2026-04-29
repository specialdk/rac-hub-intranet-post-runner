"""HTTP client for the four backend endpoints the runner calls.

All calls use header `X-Skill-Secret: <SKILL_NOTIFY_SECRET>`. Endpoints live
on the deployed backend at `${BACKEND_URL}` (Railway URL by default; override
via env var for local-against-local testing).

Error categorisation per SKILL.md §2g:

  - **Permanent**: 4xx with a parseable JSON body — submission won't succeed
    on retry without intervention. Skill calls /skill/quarantine.
  - **Transient**: 5xx, network failure, or unparseable JSON — system is
    just unavailable. Skill skips and retries on the next run.
  - **Auth**: 401 BAD_SECRET — separate from validation; treated as a
    configuration error and surfaced loudly.

These three classes (PermanentBackendError, TransientBackendError,
AuthBackendError) are caught by the orchestrator in intranet_post.py.
"""

from __future__ import annotations

import os
from typing import Any

import requests


# ---------------------------------------------------------------------------
# Exception taxonomy
# ---------------------------------------------------------------------------

class BackendError(Exception):
    """Base class — never raised directly."""


class PermanentBackendError(BackendError):
    """Backend returned a 4xx with a clear error code. Submission is broken."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.status = status


class TransientBackendError(BackendError):
    """Network / 5xx / unparseable response. Try again on the next run."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AuthBackendError(BackendError):
    """X-Skill-Secret rejected. Configuration error — fail the run."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = (10, 60)  # (connect, read) seconds


def _backend_url() -> str:
    url = os.environ.get("BACKEND_URL", "").rstrip("/")
    if not url:
        raise RuntimeError("BACKEND_URL env var is not set")
    return url


def _secret() -> str:
    s = os.environ.get("SKILL_NOTIFY_SECRET", "")
    if not s:
        raise RuntimeError("SKILL_NOTIFY_SECRET env var is not set")
    return s


def _headers() -> dict[str, str]:
    return {
        "X-Skill-Secret": _secret(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request(method: str, path: str, *, json_body: dict | None = None, params: dict | None = None) -> dict:
    """Make a backend request and return the parsed JSON body.

    Raises one of the three BackendError subclasses on failure. Successful
    response JSON is returned with `ok: True` and any extra fields the
    endpoint provides.
    """
    url = f"{_backend_url()}{path}"
    try:
        resp = requests.request(
            method,
            url,
            headers=_headers(),
            json=json_body,
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
    except (requests.ConnectionError, requests.Timeout) as e:
        raise TransientBackendError(f"network error talking to backend: {e}") from e
    except requests.RequestException as e:
        raise TransientBackendError(f"unexpected requests error: {e}") from e

    # 5xx: treat as transient — skill should retry next run
    if 500 <= resp.status_code < 600:
        raise TransientBackendError(
            f"backend returned {resp.status_code}: {resp.text[:200]}"
        )

    # Parse body — needed for both success and 4xx error reporting
    try:
        body = resp.json()
    except ValueError:
        if resp.status_code == 200:
            raise TransientBackendError(
                f"backend returned 200 but body wasn't JSON: {resp.text[:200]}"
            )
        # Non-200 + non-JSON: also transient (probably an HTML error page)
        raise TransientBackendError(
            f"backend returned {resp.status_code} with non-JSON body: {resp.text[:200]}"
        )

    if resp.status_code == 401 and isinstance(body, dict) and body.get("error") == "BAD_SECRET":
        raise AuthBackendError("backend rejected X-Skill-Secret — check SKILL_NOTIFY_SECRET env var")

    if 400 <= resp.status_code < 500:
        code = body.get("error", "UNKNOWN") if isinstance(body, dict) else "UNKNOWN"
        message = body.get("message", "") if isinstance(body, dict) else resp.text[:200]
        raise PermanentBackendError(code, message, resp.status_code)

    if not isinstance(body, dict) or not body.get("ok"):
        # Backend returned 200 but ok != True — treat as permanent
        code = body.get("error", "UNKNOWN") if isinstance(body, dict) else "UNKNOWN"
        message = body.get("message", "") if isinstance(body, dict) else ""
        raise PermanentBackendError(code, message, resp.status_code)

    return body


# ---------------------------------------------------------------------------
# Endpoint wrappers
# ---------------------------------------------------------------------------

def get_pending() -> list[dict[str, Any]]:
    """GET /skill/pending — returns the array of pending submissions.

    Each entry has either `submission` (parsed submission.json) or `error`
    (MISSING_SUBMISSION_JSON / INVALID_SUBMISSION_JSON). The caller decides
    per-item whether to process or quarantine.
    """
    body = _request("GET", "/skill/pending")
    return list(body.get("submissions") or [])


def process(
    *,
    folder_id: str,
    cleaned_text: str,
    resolved_title: str,
    resolved_highlight: str,
    admin_note: str = "",
) -> dict[str, Any]:
    """POST /skill/process — atomic upload + sheet write + folder move.

    Returns the success body, which includes `destination`, `banner_url`,
    `body_urls`. Note: as of this version, the backend does not return
    `row_number` directly — we reconstruct or look it up if needed for
    /admin/notify.
    """
    return _request(
        "POST",
        "/skill/process",
        json_body={
            "folder_id": folder_id,
            "cleaned_text": cleaned_text,
            "resolved_title": resolved_title,
            "resolved_highlight": resolved_highlight,
            "admin_note": admin_note,
        },
    )


def quarantine(*, folder_id: str, error_text: str) -> None:
    """POST /skill/quarantine — moves folder to Quarantine/ with error.txt."""
    _request(
        "POST",
        "/skill/quarantine",
        json_body={"folder_id": folder_id, "error_text": error_text},
    )


def notify_admin(
    *,
    destination: str,
    row_number: int,
    title: str,
    submitted_by: str,
) -> None:
    """POST /admin/notify — sends the review email via Resend.

    Failure here is logged but doesn't quarantine. The submission still made
    it to the sheet; only the email is missing, and admin can find pending
    rows via the PWA's queue regardless.
    """
    _request(
        "POST",
        "/admin/notify",
        json_body={
            "destination": destination,
            "row_number": row_number,
            "title": title,
            "submitted_by": submitted_by,
        },
    )
