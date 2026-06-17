# SESSION 01 — 17 Jun 2026

_Per-session log. Historical record, not current truth — for current facts see
`BARDACHD_CLAUDE.md`; for outstanding work see `BARDACHD_TODO.md`. Read the most
recent SESSION_*.md for "where we left off" context._

## Goal of this session
Take Bàrdachd from "exists only in project knowledge" to a real, pushed repo
with the source on disk — i.e. work down the first half of `BARDACHD_TODO.md`
("get to first deploy", local side).

## What was done
- **Confirmed Bàrdachd = Prosody renamed.** Settled the ambiguity between the
  Prosody docs and the Bàrdachd CLAUDE.md: same FastAPI codebase, one app, the
  Prosody name is history.
- **Set up the four project docs** (done in an earlier part of the session):
  `BARDACHD_CLAUDE.md`, `BARDACHD_TODO.md`, `BARDACHD_PROJECT_NOTES.md`, and a
  paste-in additions block for `PI-INFRASTRUCTURE.md`. Resolved the CLAUDE.md
  TBCs from the real code: port **8200**, flat layout (no `backend/`),
  single-user/no-auth with an auto-committing `db()`.
- **Settled casing.** Mac dev root is `/Users/callummaclellan/Bardachd`
  (capital B, matches disk); Pi clone dir, service name and Funnel path stay
  lowercase `bardachd` (intentional — don't "align" them).
- **Saved the source to disk** under the dev root: `main.py` (unchanged from the
  project-knowledge snapshot), `frontend.py` (with the prefix fix below),
  `requirements.txt` (`fastapi`, `uvicorn`, `pronouncing`), `.gitignore`.
- **Applied the prefix fix to `frontend.py`** — the one landmine flagged in
  CLAUDE.md. Folded it into the first on-disk version so there's no broken
  commit in history (see "Key decision" below).
- **Created and pushed the repo.** `https://github.com/glenachulish/bardachd.git`,
  branch `main`, pushed clean (10 objects). HTTPS, no credential wall —
  the Mac's existing GitHub auth worked.
- **Updated CLAUDE.md** to record the repo URL in both the Key paths and Source
  truth sections (was TBC); ticked the completed items in the TODO.

## Key decision: the prefix fix, and how
The original Prosody `frontend.py` used leading-slash absolute API paths
(`fetch('/api/scan')` ×9). Under the production prefix `…ts.net/bardachd/` these
all 404 (browser resolves `/api/scan` to `…ts.net/api/scan`). Per the
PI-INFRASTRUCTURE contract: backend stays prefix-naïve (Tailscale strips the
prefix), frontend must be prefix-aware.

Chose the **JS prefix-constant** approach over `<base href>`: one constant at the
top of the script —
`const API = location.pathname.replace(/[^/]*$/, '') || '/';`
— and every fetch built from it (`fetch(API+'api/scan')`). Reason: it touches
only the fetch calls (visible, contained), whereas `<base href>` silently
affects every relative URL on the page. Works unchanged at both `/` (Mac dev)
and `/bardachd/` (prod).

Did the fix as part of the *first* save rather than committing the broken
version and patching after — so the repo's first commit is already
prefix-clean.

## What was tested (in the container, before delivery)
- Both `.py` files parse as valid Python; the extracted `<script>` passes
  `node --check`.
- App boots; all endpoints exercised via FastAPI TestClient: scan, forms, rhyme,
  exercises, and a full poem create/read/export/delete round trip — all pass.
- Design stance intact: Sonnet 18's opening line scores **0.6 / 60% on form**
  (the trochaic first-foot inversion), exactly as intended — the scorer was NOT
  "fixed" to forgive it. "Tyger Tyger burning bright" scans as trochaic
  tetrameter, matching the docs' verification line.
- Prefix logic checked in Node at `/`, `/bardachd/`, `/bardachd/index.html`, and
  empty path — all build the correct fetch URL.

## State at end of session
- Local side of "get to first deploy": **DONE.** Source on disk, prefix-fixed,
  repo live and pushed, docs current.
- **Nothing is deployed on the Pi yet.** Everything remaining in the TODO is
  Pi-side.

## Next session (in order, from BARDACHD_TODO.md)
1. Confirm nothing else on the Pi uses port **8200** (`ss -ltnp`).
2. Clone the repo to `~/bardachd` on the Pi; venv; `pip install -r
   requirements.txt --break-system-packages` (or in the venv).
3. Write `/etc/systemd/system/bardachd.service` (model on PROSODY_README.md;
   service name `bardachd`). `sudo systemctl enable --now bardachd`.
4. Add the Funnel path handler (additive):
   `sudo tailscale funnel --bg --https=443 --set-path=/bardachd http://127.0.0.1:8200`
5. Verify `…/bardachd/` works over the Funnel (scansion, rhyme, forms,
   exercises, save/export) — this is where a missed prefix bug would show.
6. **Immediately** curl the OTHER apps' paths to confirm the 443 change didn't
   disturb Ceòl / Òrain.
7. Housekeeping: add Bàrdachd's row to PI-INFRASTRUCTURE.md (draft block ready),
   set up the drift-report habit (FLAT globs).

**Read `PI-INFRASTRUCTURE.md` before touching the Funnel** — step 4 is the one
that can affect the other live apps, so do it carefully and not at the tail end
of a tired session.
