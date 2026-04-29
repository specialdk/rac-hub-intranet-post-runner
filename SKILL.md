---
name: intranet-post
description: Process pending submissions from the RAC Hub Submit app — clean dictated text, generate titles and highlights where the submitter left them blank, write rows to the IntranetControl sheet as "Waiting Approval", and notify the admin. Use when asked to process intranet submissions, run the intranet pending queue, check for new staff stories, or publish RAC Hub submissions to the Intranet. Honours the submitter's voice — never paraphrases, never alters Yolŋu words, never "fixes" names.
---

# intranet-post

**Owner:** Duane Kuru
**Status:** v1 (initial release)
**Last updated:** 2026-04-29

## Purpose

Process submissions from the RAC Hub Submit app and turn them into Pending rows on the IntranetControl sheet, ready for admin approval.

When a staff member submits a story through the app, their content lands as a folder in Drive. This skill picks up those folders, lightly cleans the text, generates a title and highlight if the submitter didn't write them, asks the backend to upload images and write the sheet rows, then triggers the admin notification email.

The skill exists to remove the manual editorial work between "submission lands" and "admin reviews" — making contribution painless for staff and review fast for admins. The whole point of the rac-hub-submit system is to encourage real-time contribution; this skill is what makes that contribution publishable.

---

## When to run

**Manual:** Run on demand from CoWork when you want to process pending submissions immediately.

**Scheduled (recommended):** Hourly, between 7am and 5pm local time on weekdays. Set up via Windows Task Scheduler invoking CoWork with this skill as the target.

---

## Inputs

None. The skill discovers pending work by calling `GET /skill/pending`.

---

## Reference materials

Before generating any text, read these files in order:

1. **`reference/text-cleaning-rules.md`** — what to remove, what to preserve, what never to do
2. **`reference/rac-voice-guide.md`** — what RAC voice sounds like
3. **`reference/example-titles.md`** — patterns for title generation
4. **`reference/example-highlights.md`** — patterns for highlight generation

These files are not optional reading. The skill's quality is the quality of how well its output matches the patterns in these references.

---

## Workflow

For each scheduled or manual run:

### Step 1 — Discover pending submissions

Call `GET /skill/pending`. Save the response.

If the response shows no pending submissions:
- Log: *"{timestamp}: no pending submissions"*
- Stop the run cleanly.

If there are pending submissions, proceed to Step 2 for each one in order.

### Step 2 — For each submission

#### 2a. Read submission.json

The response from `/skill/pending` includes the full `submission.json` content for each folder. Read it carefully.

Note in particular:
- `text` — the story body (may need cleaning)
- `title_suggestion` — null if submitter left blank, string if they wrote one
- `highlight_suggestion` — null if submitter left blank, string if they wrote one
- `destination` — drives which sheet tab(s) get written to
- `submitted_by` — submitter's display name from the IntranetControl Users tab
- `submitted_at` — ISO timestamp **with local timezone offset** (e.g. `+09:30`); preserve exactly, do not normalise to UTC

#### 2b. Clean the body text

Apply the rules from `reference/text-cleaning-rules.md` to the `text` field only.

**The first decision is whether cleaning is even needed.** If the text reads cleanly already — no fillers, complete sentences, natural voice — pass it through unchanged.

If cleaning is needed, apply rules in order:

1. Remove filler words (um, uh, like-as-filler, you know, sort-of/kind-of as hedge, basically, literally)
2. Strip stutters and immediate self-corrections
3. Remove swear words cleanly (delete and repair grammar; do not asterisk)
4. Capitalise sentence starts; add terminal punctuation if missing
5. Add paragraph breaks at obvious topic shifts in long dictated text

**Hard rules — these are not negotiable:**
- Never paraphrase or "improve" the writing
- Never reorder sentences
- Never add information that wasn't in the submission
- Never alter proper names exactly as written
- Never alter Yolŋu words or any non-English content
- Never "fix" Aboriginal English or Australian vernacular that's part of voice

**Track what was changed** for the AdminNote in step 2e. Count fillers removed, swears removed, stutters fixed. If nothing was changed, that's a "verbatim" outcome.

#### 2c. Generate title (if needed)

If `title_suggestion` is null:
- Read `reference/example-titles.md` and `reference/rac-voice-guide.md` first
- Generate a title from the **cleaned** text (not the raw text)
- Constraints: 2–6 words, sentence case, no emoji, no clickbait
- Lead with the most concrete element — a name, a project, an action
- Cross-check: would this look at home next to "Yanawal Kitchen" or "Tripod does it Again!"? If not, redo.

If `title_suggestion` is not null:
- Use the submitter's title verbatim. Do not "improve" it. Do not even fix typos — submitters know what they wrote.

#### 2d. Generate highlight (if needed)

If `highlight_suggestion` is null:
- Read `reference/example-highlights.md` and `reference/rac-voice-guide.md` first
- Generate a highlight from the **cleaned** text
- Constraints: 5–15 words typically (up to 30 for multi-event recaps), warm, specific
- Optional: one emoji at the end if it adds genuine meaning. Skip if uncertain.
- Match the *feeling* — pride, joy, welcome, progress, concern (for safety)

If `highlight_suggestion` is not null:
- Use the submitter's highlight verbatim.

#### 2e. Compose AdminNote

A short summary of what the skill did, written for the admin who will review the row.

Format: `"Auto-cleaned: [count] fillers, [count] swears removed. [other actions]"`

Examples:
- `"Auto-cleaned: 3 fillers, 1 swear removed. Title generated."`
- `"Auto-cleaned: 2 fillers removed. Submitter's title and highlight used verbatim."`
- `"Submitter's text used verbatim. Title and highlight generated."`
- `"Submitter's text, title and highlight used verbatim."`

Keep it short — it has to fit in a sheet column.

If the body text contains an enumerated list that could benefit from bullet formatting on review, append: *" Note: body contains an enumerated list that could be bulleted on review."* This is a heads-up to the reviewer, not an action the skill takes.

#### 2f. Submit to backend

Call `POST /skill/process` with:

```json
{
  "folder_id": "<folder ID from /skill/pending response>",
  "cleaned_text": "<the cleaned text from step 2b>",
  "resolved_title": "<submitter's title or generated>",
  "resolved_highlight": "<submitter's highlight or generated>",
  "admin_note": "<the AdminNote from step 2e>"
}
```

The backend handles, atomically:
- Image upload to `Intranet Photos/`
- ContentNumber computation
- Sheet row insertion (one row for Manager destinations, two rows for General — Modal Stories + Hero Content with matching ContentNumber/SlideNumber)
- Folder move from `Intranet Submissions/` to `Intranet Submissions Processed/`
- AdminNote written to Manager tabs col J or Modal Stories col K (only if header literally says "AdminNote"); never on Hero Content

Status value written to the sheet is **`"Waiting Approval"`** (the v1 terminology, replacing the old "Pending").

#### 2g. Handle the response

**On success** (`{"ok": true, ...}`):

Call `POST /admin/notify` with:

```json
{
  "destination": "<destination from submission.json>",
  "row_number": "<row from /skill/process response>",
  "title": "<resolved_title>",
  "submitted_by": "<submitted_by from submission.json>"
}
```

The admin gets an email with a deep link to review the row.

Append to today's log:
> `{timestamp}: processed {folder_name} → {destination} row {row}. Title: "{title}". {AdminNote}`

**On failure** (`{"ok": false, "error_code": "...", "error_message": "..."}`):

This means the backend hit a permanent error (validation reject, schema mismatch, etc.) — the submission won't succeed on retry without intervention.

Call `POST /skill/quarantine` with:

```json
{
  "folder_id": "<folder ID>",
  "error_message": "<error_message from /skill/process response>"
}
```

The folder moves to `Intranet Submissions Quarantine/` with an `error.txt` file alongside it.

Append to today's log:
> `{timestamp}: quarantined {folder_name}. Reason: {error_message}`

**On network failure or 5xx** (no JSON response, or HTTP 500/502/503):

This is a transient failure. Don't quarantine — the submission is still valid, the system is just unavailable.

- Append to today's log: `{timestamp}: skipped {folder_name} due to transient backend error: {error}. Will retry on next run.`
- Do not call `/skill/quarantine`.
- Move on to the next submission, or end the run if no more pending.

The folder remains in `Intranet Submissions/` and will be picked up on the next scheduled run.

### Step 3 — Run summary

Once all pending submissions are processed:

Append to today's log:
> `{timestamp}: run complete. Processed: {N}, Succeeded: {M}, Quarantined: {K}, Skipped (transient): {S}.`

---

## Endpoints reference

All endpoints use header `X-Skill-Secret: <SKILL_NOTIFY_SECRET>`. Auth failure returns `{"ok": false, "error": "BAD_SECRET"}` HTTP 401.

| Endpoint | Method | Purpose |
|---|---|---|
| `https://rac-backend.up.railway.app/skill/pending` | GET | List pending submissions with their submission.json contents |
| `https://rac-backend.up.railway.app/skill/process` | POST | Process one submission atomically (uploads, writes, folder move) |
| `https://rac-backend.up.railway.app/skill/quarantine` | POST | Move a failed submission to Quarantine/ with error.txt |
| `https://rac-backend.up.railway.app/admin/notify` | POST | Send admin notification email after successful processing |

Full request/response shapes are in `backend/README.md` of the rac-hub-submit repo. The skill plan (`intranet-post-skill-plan.md`) §5 also documents them.

---

## Logging

Append-only daily log in `logs/{YYYY-MM-DD}.log`.

Each log line is plain text, one entry per line, prefixed with an ISO timestamp.

**Why a daily file:** keeps log files manageable in size, makes it easy to ask "what happened today?" without parsing months of history.

**What to log:**
- Run start and end markers (with summary stats at end)
- Each submission processed (success, with folder name, destination, row, title)
- Each quarantine (with folder name and reason)
- Each transient skip (with folder name and reason)
- Any unexpected error (with stack-trace-equivalent context)

Don't log the full submission.json content — too noisy. Don't log the cleaned text — use the AdminNote instead, which captures what changed.

---

## Edge cases and how to handle them

### Submitter wrote a great title and highlight; text is also clean

The skill should do nothing creative. Pass everything through verbatim. AdminNote: *"Submitter's text, title and highlight used verbatim."*

This is the **best possible outcome**. Don't override good work to feel useful.

### Submission has very thin text (e.g. "team day at the kitchen")

Clean what's there (capitalise, punctuate). Generate title and highlight from what's available, leaning on context (folder name, destination, photos in folder). Don't fabricate details.

If you genuinely can't generate something honest, generate something short and accurate — *"Team photo"* is a valid highlight. Don't pad to look thorough.

### Submission contains a swear word in reported speech / quotation

Borderline. If clearly inside quotation marks (e.g. `"Sam said 'this bloody trailer wouldn't start'"`) — keep, it's reported speech. If in the submitter's own narration — clean.

### Submission contains Yolŋu words you don't recognise

**Leave them exactly as written.** Always. No spelling changes. No translations added. No italicisation. Treat unknown words as deliberate choices unless context strongly suggests otherwise.

### Submission contains what looks like a typo in a name

**Leave it.** Submitters know how to spell their colleagues' names. The cost of treating a name as a typo (offending someone) is much higher than the cost of treating a typo as a name (one strange spelling on the Intranet that the admin will see and decide on).

### Submission text is malformed (not valid for cleaning)

Quarantine. Error message: *"Submission text could not be parsed for cleaning: [specific issue]"*. Better the admin sees this and intervenes than the skill produces garbage.

### Backend returns success but row write looks wrong on later inspection

Out of scope for the skill. The skill trusted the backend's success response. If something downstream of the skill is wrong, that's a backend bug, not a skill bug. Log normally.

### Two submissions land at exactly the same time

The backend handles ContentNumber assignment atomically. Each submission gets a unique number. The skill processes them sequentially regardless of when they arrived; ordering is by whatever order `/skill/pending` returns them.

### A submission has been in Submissions/ for several runs without being processed

This means transient failures keep happening for that specific submission. After 5 consecutive failed runs on the same folder, log a warning so the admin can investigate. The skill itself doesn't quarantine on transient failures — that's an admin call.

---

## What the skill does NOT do

These are deliberate scope decisions for v1:

- **No body formatting beyond paragraph breaks.** The skill doesn't add bullets, bold, headers, or emojis to body text. It just adds paragraph breaks where needed. (Seen patterns are surfaced in the AdminNote as a suggestion to the reviewer.)
- **No retroactive editing.** Once a row is written, the skill never touches it again. Approval, archiving, and edits are admin-side concerns.
- **No image processing.** Image upload, ordering, banner identification — all backend responsibilities. The skill doesn't look at image files.
- **No deletion or destruction.** The skill never deletes folders, never removes rows, never overwrites data. Folders move (Submissions → Processed or Quarantine); rows get written, never deleted.
- **No human notification beyond the admin email.** Submitters don't get acknowledgement emails from the skill. (That could be a v1.5 feature.)

---

## How to extend this skill

When the skill needs to handle a new edge case, the change usually goes in one of three places:

**Reference files** (`reference/*.md`): if the issue is about *what good output looks like* — voice, examples, patterns — update the reference files. The skill picks up new patterns automatically.

**Cleaning rules** (`reference/text-cleaning-rules.md`): if the issue is about *what to clean or preserve* — a new filler word, a new swear, a new "leave alone" pattern — update the rules file.

**This SKILL.md** (workflow section): if the issue is about *order of operations or new steps* — a new endpoint, a new check, a different decision flow — update the workflow.

**Backend** (rac-hub-submit/backend/): if the issue is about *what the backend does* — a new field in the sheet, a different folder structure — that's a backend change, not a skill change. Coordinate with whoever maintains the backend.

The hierarchy when in doubt: prefer reference file updates first (cheapest), workflow changes second, backend changes last.

---

## Author's note

This skill is the closing piece of the rac-hub-submit system. The app makes contribution easy. The backend makes the data flow safe. This skill makes the editorial work invisible — turning raw, fast, sometimes-rough submissions into Intranet-ready content without anyone having to think about it.

The most important thing the skill does is **honour the submitter's voice**. RAC's published content sounds like RAC because real people wrote it. This skill's job is to clean dictation artefacts and fill in blanks, never to replace the submitter's voice with something more "polished."

When in doubt, do less.
