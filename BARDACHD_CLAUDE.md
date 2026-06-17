# Bàrdachd – Poetry Writing Companion (CLAUDE.md)

_Created 16 Jun 2026. Updated 17 Jun 2026: confirmed Bàrdachd **is** the app
formerly drafted as "Prosody" — same FastAPI codebase, renamed. The earlier
"assumed" architecture notes have been replaced with the real values from the
code now in project knowledge (`prosody_main_py.txt`, `prosody_frontend_py.txt`).
This file lives in the repo root AND in project knowledge. If they disagree, the
repo copy wins. If this file disagrees with the code, the code wins — see
"Source truth" below._

## What this is
A personal poetry-writing app: a workshop in metre and rhyme. Live scansion
(stress dots per syllable, names the metre), a rhyme finder (perfect + near/
slant), a fixed-form library (sonnet, villanelle, ballad, haiku, limerick,
heroic couplet, quatrain) with a per-line stress-pattern target overlay, guided
ear-training exercises, and save/export of poems. Grounded in standard
public-domain prosody — **not** a reproduction of any copyrighted book's
exercises or examples; all exercise text and form notes are original wording
built on public-domain mechanics. Keep it that way.

Mobile-friendly, served by the same Raspberry Pi over Tailscale, sibling to Ceòl
and Òrain. Callum is not a coder: Claude writes all code; Callum runs Terminal
commands and deploys.

## Status: LIVE (deployed 17 Jun 2026)
The app is deployed and running at
`https://ceol-pi.tail01672f.ts.net/bardachd/`, under `bardachd.service`
(enabled at boot) on internal port 8200, served at `/bardachd/` on the shared
443 Funnel. Source on disk at the Mac dev root and in the repo (below); the
prefix fix is applied. Since first deploy it has gained three editable reference
tabs (Further reading / Websites / Media) and PWA install support — see
`BARDACHD_PROJECT_NOTES.md` for how those work, and `BARDACHD_SESSION_02.md` /
`SESSION_03.md` for the deploy and feature history. The systemd unit and run
commands in `PROSODY_README.md` are now the *actual* setup (with one deviation:
the service binds `127.0.0.1`, not `0.0.0.0`).

## Source truth — read this first
- **Never trust snapshots or session notes over live code.** A fresh session
  should clone the real branch inside its container and inspect that:
  `git clone --depth 1 --branch main https://github.com/glenachulish/bardachd.git`
- The repo is the source of truth. The `prosody_main_py.txt` /
  `prosody_frontend_py.txt` files in project knowledge are the *original*
  pre-deploy snapshot (now saved to disk as `main.py` / `frontend.py` with the
  prefix fix applied) — treat them as history, not current code.
- Project knowledge holds session notes, the TODO, and this file — NOT (long
  term) live source. Inspect code in the clone; test patches before delivery.
- Invisible to a clone (gitignored): `data/` (the `poems.db` SQLite store),
  `.venv/`, `.backups/`. There are no secrets in this app (no auth, no keys).

## ⚠️ The one landmine to fix BEFORE first deploy: prefix-awareness
This is the single most important thing in this file. Bàrdachd will be served
on the Pi behind a **path prefix** (`…ts.net/bardachd/`), not at the root —
because the Pi's Funnel allows only three public ports and all apps share port
443 by path. See `PI-INFRASTRUCTURE.md` for the full contract.

**The current `frontend.py` is NOT prefix-aware and will break under the
prefix.** Every API call in it is a leading-slash absolute path —
`fetch('/api/scan')`, `/api/forms`, `/api/rhymes/…`, `/api/poems`,
`/api/exercises`, `/api/poems/{id}/export`. Under `/bardachd/`, the browser
resolves `/api/scan` to `…ts.net/api/scan` (404), not
`…ts.net/bardachd/api/scan`. The HTML loads; every API call then 404s.

**The fix (do it once, before deploy):** make the frontend prefix-aware. The
backend does NOT change — Tailscale strips the prefix, so from the backend's own
view it still lives at `/` (proven by Òrain; see `PI-INFRASTRUCTURE.md`).
Simplest robust approach for this single-page app: derive a base prefix in JS
from `window.location.pathname` (everything up to and including `/bardachd/`)
and build every fetch URL from it, or set a `<base href>` and switch all fetches
to relative paths (`api/scan`, not `/api/scan`). Either works; pick one and keep
it consistent. **Backend = prefix-naïve; frontend = prefix-aware.**

Doing this now is cheap. Retrofitting later (the Ceòl story in
`PI-INFRASTRUCTURE.md`) is the expensive path.

## Architecture (confirmed from the code, not assumed)
- **Backend**: FastAPI, single file `main.py`. Contains the scansion engine
  (CMU pronouncing dictionary via the `pronouncing` library), rhyme/syllable
  helpers, the form library, exercises, the per-line target-pattern logic, and
  all API routes. It serves the UI at `/` by importing the `HTML` string from
  `frontend.py`.
- **Frontend**: `frontend.py` is one big `HTML` string (HTML/CSS/JS) for the
  whole single-page UI. Vanilla JS, no build step.
- **Database**: SQLite, `poems.db`, created automatically on first run. A single
  `db()` context manager that **auto-commits** (`yield conn; conn.commit()`).
- **Auth**: NONE. Single-user app, no accounts, no cookies, no secrets. This is
  a deliberate, settled decision (the app is personal and private behind
  Tailscale) — do NOT add auth unless the requirement actually changes.
- **Layout on disk**: FLAT — `main.py` and `frontend.py` in one directory, plus
  `poems.db`. No `backend/` subfolder (unlike Ceòl). Deploy commands and any
  drift report must use flat globs (`*.py`), not `backend/*.py`.
- **Dependencies**: `fastapi`, `uvicorn`, `pronouncing`.

## Key paths & endpoints — confirmed where known, FILL IN the rest
- Mac dev root: `/Users/callummaclellan/Bardachd` (capital B — matches the real
  folder on disk; note the Pi clone dir below is lowercase `bardachd`)
- GitHub repo + branch: `https://github.com/glenachulish/bardachd.git`, branch
  `main`. Clone for a fresh session:
  `git clone --depth 1 --branch main https://github.com/glenachulish/bardachd.git`
- Pi service name: `bardachd` (unique — NOT `ceol`, NOT `prosody`)
- Internal port: **8200** (confirmed from the code's run command; unique on the
  Pi — Ceòl :8001, Òrain :8004, Shadowing :8003, so :8200 is clear)
- Funnel exposure: **path-based on 443**, served at `/bardachd/`, following
  Òrain's proven pattern. Exact command (confirm Tailscale version at the time):
  `sudo tailscale funnel --bg --https=443 --set-path=/bardachd http://127.0.0.1:8200`
  Internal localhost ports are unlimited; only the public 443/8443/10000 face is
  constrained. See `PI-INFRASTRUCTURE.md` — read it before touching Funnel.
- Data dir: `poems.db` sits beside `main.py` by default (the code uses
  `Path(__file__).parent / "poems.db"`). If you want it isolated like Òrain's,
  add an env var (e.g. `BARDACHD_DATA_DIR`) — optional, not required, since the
  DB name doesn't collide with Ceòl's or Òrain's anyway.

## Patch & deploy conventions (same discipline as Ceòl)
- Python direct-replace patch scripts (never `git am`): backup first, verify
  each anchor appears exactly once, `node --check` for any JS work, idempotent
  via a marker string, delivered to `~/Downloads/`.
- Instructions for Callum: plain language, WHY before HOW, single self-contained
  copy-paste blocks (zsh chokes on multi-line pastes).
- Standard deploy (always Mac AND Pi) — fill in real repo/branch once they exist:
  1. run patch script locally
  2. `cd /Users/callummaclellan/Bardachd && git add -A && git commit -m '...' && git push origin <BRANCH>`
  3. `ssh -t pi@ceol-pi.local 'cd ~/bardachd && git pull origin <BRANCH> && sudo systemctl restart bardachd'`
     (`-t` is required so sudo can prompt; never pipe the password)

## Environment quirks (shared with the Pi)
- Pi OS Bookworm: pip needs `--break-system-packages`; no `sqlite3` CLI — use
  `python3 -c` with the sqlite3 module.
- Python on the Pi is 3.13.x.
- Pi log: `ssh pi@ceol-pi.local 'sudo journalctl -u bardachd -n 50 --no-pager'`

## Design stance to preserve (don't "fix" it)
Form-matching scores against STRICT metre on purpose. A deliberate, skilful
variation — like the trochaic first-foot inversion opening Sonnet 18 — reads as
"60% on form." That's intended: the overlay shows where a line departs from the
template; whether that's a mistake or a good variation is the writer's judgement.
A red dot is a question ("did I mean that?"), not a verdict. Don't "correct" the
scorer to forgive variations.

Also intrinsic, don't change without a reason: monosyllables are resolved by a
function-word heuristic (so the metre label is a strong hint, not gospel) and
unknown words are flagged, never guessed.

## Where status lives
- `BARDACHD_TODO.md` — current outstanding work (starts with: get to first deploy).
- `BARDACHD_PROJECT_NOTES.md` — distilled long-term knowledge (built from the old
  Prosody context doc).
- `SESSION_*.md` — per-session history; historical record, not current truth.
  Starts empty; accumulates per session.
- `PI-INFRASTRUCTURE.md` — shared Pi/Tailscale/Funnel reference.
