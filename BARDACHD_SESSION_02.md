# SESSION 02 — 17 Jun 2026

_Per-session log. Historical record, not current truth — for current facts see
`BARDACHD_CLAUDE.md`; for outstanding work see `BARDACHD_TODO.md`. Read the most
recent SESSION_*.md for "where we left off" context._

## Goal of this session
The Pi-side deploy: get Bàrdachd running on `ceol-pi` under systemd and served
over the Funnel at `/bardachd/`, following the ordered Pi-side list from
SESSION_01 — **without taking the live neighbour apps (Ceòl, Òrain, Nature,
Skywards) offline.** Reversibility was the explicit priority.

## Outcome: DEPLOYED SUCCESSFULLY
Bàrdachd is live at `https://ceol-pi.tail01672f.ts.net/bardachd/`, running under
`bardachd.service` (enabled at boot), on internal port 8200. No neighbour app
was disturbed. No rollback was needed at any step.

## Captured baseline (the known-good state, BEFORE any change)
Saved on the Pi as `~/funnel-baseline-20260617.txt`. Recorded here too so it
lives off the Pi.

### Funnel handler map at start of session
Port 443 had **four** path handlers (more than PI-INFRASTRUCTURE.md knew about —
Nature and Skywards had been added since that doc was written):

| Public path (443) | proxies to | app |
|---|---|---|
| `/`        | `http://127.0.0.1:8080` | Ceòl (root alias — DEAD, see below) |
| `/orain`   | `http://127.0.0.1:8004` | Òrain |
| `/nature`  | `http://127.0.0.1:8085` | Nature |
| `/skyward` | `http://127.0.0.1:8005` | Skywards |

Plus `:8443` → `https+insecure://localhost:8001` (Ceòl's real TLS face) and
`:10000` → `http://localhost:8003` (Gàidhlig Shadowing).

### Listening ports at start (`ss -ltnp`)
:8085 (Nature), :8005 (Skywards), :8004 (Òrain), :8003 (Shadowing),
:8001 (Ceòl real backend) — all live. **:8200 was free** (our target).
**:8080 had nothing listening** — so Ceòl's `/`→:8080 handler on 443 is a dead
alias; the live Ceòl is the 8443→:8001 path. This matches the 2026-05-31
correction in PI-INFRASTRUCTURE.md. **Pre-existing; not caused by this session.**

## What was done (in order, each verified before the next)
1. **SSH + baseline capture.** Saved `tailscale serve status` (+ `--json`) to
   `~/funnel-baseline-20260617.txt`; captured `ss -ltnp`. Confirmed 8200 free.
2. **Cloned the repo** to `~/bardachd` (lowercase) and built a venv at
   `~/bardachd/.venv`; `pip install -r requirements.txt` (fastapi, uvicorn,
   pronouncing) — all satisfied. (Reversible: just a new directory.)
3. **Smoke test** on a throwaway backgrounded uvicorn on :8200 — `/api/forms`
   returned JSON; then killed it, confirmed 8200 free again.
4. **systemd service.** Wrote `/etc/systemd/system/bardachd.service`
   (User=pi, WorkingDirectory=/home/pi/bardachd, ExecStart uvicorn on
   `127.0.0.1:8200`, Restart=on-failure). `enable --now` → `active`. Verified it
   serves `/api/forms` and listens on 127.0.0.1:8200.
   - **One intentional deviation from PROSODY_README's unit:** bound to
     `127.0.0.1`, not `0.0.0.0` — the app only needs to be reachable by
     Tailscale on localhost, matching how Òrain/Ceòl bind. Never directly
     exposed.
5. **Funnel handler added (the one risky step).** Forward command:
   `sudo tailscale funnel --bg --https=443 --set-path=/bardachd http://127.0.0.1:8200`
   `--set-path` confirmed **additive** — the command printed all FIVE paths;
   the four existing handlers were untouched. (This is now the 4th+ time
   `--set-path` has been used additively on this setup; the behaviour is solid.)
6. **Funnel verification.** Over the public URL:
   - `…/bardachd/api/forms` → forms JSON (backend reached correctly through the
     stripped prefix — proves the SESSION_01 prefix fix works in production).
   - `…/bardachd/` → homepage HTML loads.
7. **Neighbour safety check (the whole point of the reversibility discipline).**
   - `/orain/` → 200 ✓
   - `/nature/` → 200 ✓
   - `/skyward/` → 200 ✓
   - `/` (Ceòl root alias) → 502 — **pre-existing dead :8080 handler, not us**
     (it had nothing listening in the step-1 baseline, before any change).
   - Ceòl's real face `:8443/` → 307 ✓ (healthy, as the infra doc predicts).

## Rollback commands (had on hand BEFORE step 4; not needed, recorded for future)
- **Targeted undo of the bardachd path** (leaves the other four intact):
  `sudo tailscale funnel --https=443 --set-path=/bardachd off --yes`
- **Full baseline restore** (re-assert all four existing handlers if anything
  shifts):
  ```
  sudo tailscale funnel --bg --https=443 --set-path=/ http://127.0.0.1:8080
  sudo tailscale funnel --bg --https=443 --set-path=/orain http://127.0.0.1:8004
  sudo tailscale funnel --bg --https=443 --set-path=/nature http://127.0.0.1:8085
  sudo tailscale funnel --bg --https=443 --set-path=/skyward http://127.0.0.1:8005
  ```
- **Undo the service (step 3):**
  `sudo systemctl disable --now bardachd && sudo rm /etc/systemd/system/bardachd.service && sudo systemctl daemon-reload`
- **Undo the clone (step 2):** `rm -rf ~/bardachd`

## State at end of session
- Bàrdachd **deployed and live** at `/bardachd/`, under `bardachd.service`
  (enabled at boot), internal port 8200.
- All neighbour apps confirmed healthy.
- **Still to do by Callum:** open `…/bardachd/` in a browser and confirm the
  interactive features work live (scansion dots, rhyme finder, load a form
  skeleton, exercises, a save/export round trip). curl proves backend + prefix;
  the browser confirms the frontend JS wires up — the last place a prefix bug
  could hide.

## Next session / remaining housekeeping
1. Browser-verify the live UI (above) if not done this session.
2. Update PI-INFRASTRUCTURE.md's live-state table + target architecture to
   include Bàrdachd (`/bardachd` → :8200) — AND correct it to show Nature and
   Skywards on 443, which it currently omits. The draft addition block lives in
   `PI-INFRASTRUCTURE-bardachd-additions.md` (will need extending to cover
   Nature/Skywards too).
3. Set up the drift-report habit (`DRIFT-REPORT-HABIT.md`) with **FLAT** globs
   (`*.py`, not `backend/*.py`), tracking `main.py`, `frontend.py`, and the
   status/notes docs. Use `DRIFT-STEP0-TEMPLATE.md`.

## Note for the infra doc (carry forward)
PI-INFRASTRUCTURE.md is now stale in two ways worth fixing when next editing it:
(a) it lists only Ceòl + Òrain on 443, but Nature (:8085) and Skywards (:8005)
are also there; (b) the dead `/`→:8080 Ceòl root alias is still live as a
handler returning 502 — a Ceòl-project cleanup item, untouched here.
