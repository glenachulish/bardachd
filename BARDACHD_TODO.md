# Bàrdachd — TODO

_The single current outstanding-work list. As of 17 Jun 2026 the app exists only
in project knowledge: no repo, nothing on disk, nothing on the Pi. So this list
is mostly "get to first deploy." Reorder/strike as things land._

## Before anything else
- [x] **Mac dev root confirmed:** `/Users/callummaclellan/Bardachd` (capital B,
      matches the folder on disk). Pi clone dir stays lowercase `~/bardachd` to
      match the service name and Òrain convention — intentional, don't "align".

## Get the source onto disk and into a repo
- [ ] Save the two project-knowledge files to disk under the dev root, renamed:
      `prosody_main_py.txt` → `main.py`, `prosody_frontend_py.txt` → `frontend.py`.
- [ ] Add `requirements.txt` (`fastapi`, `uvicorn`, `pronouncing`) — referenced
      by `PROSODY_README.md` but not yet in project knowledge.
- [ ] Add a `.gitignore`: `data/` (or just `poems.db`), `.venv/`, `.backups/`,
      `__pycache__/`.
- [ ] Create the **new** GitHub repo (NOT glenachulish/Ceol). Record URL +
      branch in `CLAUDE.md`'s "Key paths" section.
- [ ] Initial commit + push.

## ⚠️ The prefix fix — do this BEFORE first deploy, not after
- [ ] Make `frontend.py` **prefix-aware** so it works under `…ts.net/bardachd/`.
      Currently every fetch is a leading-slash absolute path (`/api/scan`,
      `/api/forms`, `/api/rhymes/…`, `/api/poems`, `/api/exercises`,
      `/api/poems/{id}/export`) — all of which 404 under the prefix. Fix: derive
      a base prefix in JS from `window.location.pathname` and build every fetch
      from it, OR set `<base href>` and switch all fetches to relative paths.
      Backend stays unchanged (Tailscale strips the prefix). See `CLAUDE.md` and
      `PI-INFRASTRUCTURE.md`.
- [ ] After the fix, test locally that the app still works at `/` too (so dev on
      the Mac at `localhost:8200/` and prod at `/bardachd/` both work).

## Deploy to the Pi (follow PI-INFRASTRUCTURE.md)
- [ ] Confirm nothing else on the Pi uses port **8200** (Ceòl :8001, Òrain
      :8004, Shadowing :8003 are known; 8200 should be clear — verify).
- [ ] Clone the repo to `~/bardachd` on the Pi; make a venv; `pip install -r
      requirements.txt --break-system-packages` (or in the venv).
- [ ] Create `/etc/systemd/system/bardachd.service` (model on the unit in
      `PROSODY_README.md`, but service name `bardachd`, user/paths correct for
      the Pi). `sudo systemctl enable --now bardachd`.
- [ ] Add the Funnel path handler (additive — leaves Ceòl/Òrain untouched):
      `sudo tailscale funnel --bg --https=443 --set-path=/bardachd http://127.0.0.1:8200`
- [ ] Verify: curl `…/bardachd/api/forms` returns JSON; load `…/bardachd/` in a
      browser and confirm scansion, rhyme, forms, exercises, save/export all work
      over the Funnel (this is where a missed prefix bug shows up).
- [ ] Immediately curl the OTHER apps' paths to confirm the 443 change didn't
      disturb them.

## Housekeeping after first deploy
- [ ] Add Bàrdachd's row to `PI-INFRASTRUCTURE.md`'s live-state table and target
      architecture (a draft addition is ready — see that doc).
- [ ] Set up the drift-report habit for this project (`DRIFT-REPORT-HABIT.md`):
      generate a `drift-report.sh` with FLAT globs (`*.py`, not `backend/*.py`),
      tracking `main.py`, `frontend.py`, and the status/notes docs. Use
      `DRIFT-STEP0-TEMPLATE.md` to capture the answers.
- [ ] Start `SESSION_01.md`.

## Possible later (discussed for Prosody, not committed)
- [ ] Per-line written-out target for the line being edited (e.g. `da-DUM
      da-DUM…`).
- [ ] Stanza-grouping view (visually break a sonnet into quatrains + couplet).
- These are optional — only if Callum raises them.
