# intranet-post-runner

Autonomous Python script that closes the loop on RAC Hub Submit. Picks up pending submission folders from Google Drive (via the [rac-hub-submit backend](https://github.com/specialdk/rac-hub-submit)), cleans dictated text + generates titles and highlights using Claude, then hands off to the backend to write rows to the IntranetControl sheet as `Waiting Approval`.

Designed to run **hourly via Windows Task Scheduler** during weekday work hours. Can also be invoked by hand for ad-hoc processing.

## Architecture

This is a **consumer of the backend's API contract** — not part of the backend. The split lets each side evolve independently.

```
┌──────────────────────────────────────────────────────────────┐
│  rac-hub-submit/backend (Railway)                            │
│  ├── GET  /skill/pending      — list pending submissions     │
│  ├── POST /skill/process      — atomic upload + sheet write  │
│  ├── POST /skill/quarantine   — move folder + write error.txt│
│  └── POST /admin/notify       — email admin via Resend       │
└──────────┬───────────────────────────────────────────────────┘
           │ HTTPS + X-Skill-Secret header
           ▼
┌──────────────────────────────────────────────────────────────┐
│  intranet-post-runner (this repo, runs locally)              │
│  ├── intranet_post.py    — entry point + workflow            │
│  ├── claude_client.py    — clean / title / highlight calls   │
│  ├── backend_client.py   — HTTP wrapper for the 4 endpoints  │
│  ├── state.py            — transient-failure counter         │
│  ├── log.py              — daily log writer                  │
│  ├── SKILL.md            — workflow + editorial rules        │
│  └── reference/          — voice guide, examples, rules      │
└──────────┬───────────────────────────────────────────────────┘
           │ Anthropic API
           ▼
        Claude Opus 4.7  (cleaning + title + highlight gen)
```

`SKILL.md` and the `reference/` files are **inputs** to the script — they're loaded at runtime and passed to the Anthropic API as system context. Editing those files changes the runner's behaviour without code changes.

## Setup

1. **Python 3.10+** required.

2. **Clone and create a virtualenv:**
   ```powershell
   git clone https://github.com/specialdk/rac-hub-intranet-post-runner.git
   cd rac-hub-intranet-post-runner
   python -m venv .venv
   .venv\Scripts\Activate.ps1     # PowerShell
   # OR: .venv\Scripts\activate.bat for cmd
   pip install -r requirements.txt
   ```

3. **Copy `.env.example` to `.env`** and fill in the three required values:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   BACKEND_URL=https://rac-backend.up.railway.app
   SKILL_NOTIFY_SECRET=<must match backend's env var>
   ```

4. **Verify by running once:**
   ```powershell
   python intranet_post.py
   ```
   Expected outputs (depending on Drive state):
   - "no pending submissions" + run summary → no work to do, exit clean
   - one or more `processed ...` lines → real submissions handled

   Check `logs/YYYY-MM-DD.log` for the full transcript of what happened.

## How it works

For each pending submission returned by `GET /skill/pending`:

1. **Clean** the body text (Claude API call, system prompt = `text-cleaning-rules.md` + `rac-voice-guide.md`).
   - Filler words removed, stutters fixed, swears cleaned (unless in reported speech), paragraph breaks added at topic shifts.
   - **Yolŋu words, proper names, and Aboriginal English are NEVER altered** — these are hard rules baked into the system prompt.
   - If the text is already clean, it passes through unchanged with `verbatim: true`.

2. **Resolve title:** if the submitter wrote one, use it verbatim (typos and all — submitters know what they wrote). Otherwise generate via Claude (`example-titles.md` + voice guide).

3. **Resolve highlight:** same pattern as title (`example-highlights.md` + voice guide).

4. **Compose AdminNote** describing what was done (e.g. "Auto-cleaned: 3 fillers, 1 swear removed. Title generated."). Goes into the sheet's AdminNote column for admin context during review.

5. **Call `/skill/process`** — backend uploads images, computes ContentNumber, inserts row(s) at the top of the destination tab(s) with `Status = "Waiting Approval"`, moves folder to `Intranet Submissions Processed/`.

6. **Call `/admin/notify`** — backend emails the admin with a deep link to the review screen.

Failures fall into three buckets per `SKILL.md` §2g:
- **Transient** (network, 5xx, Claude API rate limit) → log, leave folder in place, retry next run. Per-folder counter increments; after 5 consecutive failures, a warning surfaces.
- **Permanent** (validation, schema mismatch) → quarantine: backend writes `error.txt` and moves folder to `Intranet Submissions Quarantine/`.
- **Auth** (`BAD_SECRET`) → fail fast with exit code 1; this is a configuration error, not a runtime failure.

## Scheduling

Runs hourly on weekdays between 7am and 5pm local time. Setup via **Task Scheduler**:

1. Open **Task Scheduler** (Win+R → `taskschd.msc`).
2. **Create Task** (not Basic Task — we need the full options).
3. **General tab:**
   - Name: `RAC intranet-post`
   - Description: `Process pending RAC Hub submissions hourly`
   - **Run only when user is logged on** (the script needs your Anthropic key in the user-scope env).
4. **Triggers tab → New:**
   - Begin: `On a schedule`
   - Settings: `Daily`, recur every 1 day
   - Advanced: **Repeat task every 1 hour for a duration of 10 hours**
   - Start time: `7:00:00 AM`
   - **Synchronize across time zones**: unchecked (we want local time)
   - **Days of week**: customise to weekdays only via a separate schedule, OR use a PowerShell condition wrapper (see below)
5. **Actions tab → New:**
   - Action: `Start a program`
   - Program/script: `C:\Users\speci\OneDrive\RAC-Projects\rac-hub-intranet-post-runner\.venv\Scripts\python.exe`
   - Add arguments: `intranet_post.py`
   - Start in: `C:\Users\speci\OneDrive\RAC-Projects\rac-hub-intranet-post-runner`
6. **Conditions tab:**
   - Power: uncheck "Start the task only if the computer is on AC power" if you want it to run on battery
   - Network: optional — check "Start only if the following network connection is available" → "Any connection"
7. **Settings tab:**
   - "Allow task to be run on demand": checked
   - "If the task fails, restart every": 5 minutes, up to 3 times
   - "Stop the task if it runs longer than": 10 minutes (sanity cap)

### Weekday-only

Task Scheduler's basic UI lets you pick "Weekly → Mon–Fri", which conflicts with the hourly repeat above. Two workable options:

- **Option A (simpler):** Set up two separate triggers — one weekday-pattern trigger that fires once at 7am, and use the "Repeat task every 1 hour for 10 hours" inside it. The repeat is scoped to the trigger; on weekends, no trigger fires at all.

- **Option B (PowerShell guard):** Wrap the script call in a PowerShell one-liner that checks the day of week:
  ```powershell
  if ((Get-Date).DayOfWeek -in 'Monday','Tuesday','Wednesday','Thursday','Friday') { & .\.venv\Scripts\python.exe intranet_post.py }
  ```

## Logs

Plain-text daily files under `logs/`. Format:

```
2026-04-29T11:32:15+09:30: run started
2026-04-29T11:32:18+09:30: processed 2026-04-28_21-34_duane-kuru -> General row 2. Title: "Tripod Wins". Auto-cleaned: 3 fillers removed. Title and highlight generated.
2026-04-29T11:32:22+09:30: run complete. Processed: 1, Succeeded: 1, Quarantined: 0, Skipped (transient): 0.
```

Skim today's log: `Get-Content logs\2026-04-29.log`. Per-line timestamps make it easy to correlate with backend Railway logs and Sheet history.

## State

`state.json` (gitignored) holds the per-folder transient-failure counter. Auto-pruned each run — folders that have moved out of `Intranet Submissions/` (to Processed or Quarantine) are forgotten. Counter resets on success or quarantine.

If you want to clear the counter manually (e.g. after fixing a backend issue), delete `state.json`.

## Cost

Claude Opus 4.7 with prompt caching enabled. Per-submission cost is dominated by the cached system prompts (~10–20 KB each, ~3–5K tokens). Within a single run that processes multiple submissions:

- First submission: full price for the cached prefix (~$0.05–0.10 across 3 calls).
- Subsequent submissions in the same run: cache reads at ~10% of write cost (~$0.005–0.01 each).

A typical run with 1–5 submissions costs cents. At 11 daily runs (7am–5pm hourly weekdays), monthly Anthropic spend stays comfortably under USD $10 even with the full Drive submissions backlog.

## Editorial values

The skill design embeds RAC's editorial values explicitly:

- **Never paraphrase.**
- **Never alter Yolŋu words.**
- **Never "fix" Aboriginal English or Australian vernacular.**
- **The most sophisticated thing the skill can do is sometimes nothing** — a clean submission gets passed through.

These rules live verbatim in `reference/text-cleaning-rules.md` and `reference/rac-voice-guide.md` and are passed to Claude as system context. Editing the rules edits the runner's behaviour without code changes.

The canonical worked example is **"Sam at the quarry"** in `reference/rac-voice-guide.md`. If output for that kind of submission feels natural, restrained, voice-preserved — the runner is working. If it feels inflated or AI-touched, the runner is over-reaching.
