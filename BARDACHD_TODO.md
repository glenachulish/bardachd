# Bàrdachd — TODO

_The single current outstanding-work list. **Updated 17 Jun 2026** after the Pi
deploy and the post-deploy feature work. The app is now LIVE at
`https://ceol-pi.tail01672f.ts.net/bardachd/`. Most of the original "get to
first deploy" list is done; what remains is small. Reorder/strike as things
land._

## DONE — local side (Session 01)
- [x] Mac dev root confirmed: `/Users/callummaclellan/Bardachd`.
- [x] Source saved to disk (`main.py`, `frontend.py`), `requirements.txt`,
      `.gitignore` added.
- [x] New GitHub repo created and pushed: `glenachulish/bardachd`, branch `main`.
- [x] Prefix fix applied to `frontend.py` (JS prefix constant; works at `/` and
      `/bardachd/`). Tested locally.

## DONE — Pi deploy (Session 02)
- [x] Confirmed port 8200 free; baseline of Funnel + listening ports captured.
- [x] Cloned to `~/bardachd` on the Pi; venv; requirements installed.
- [x] `bardachd.service` written and enabled (binds `127.0.0.1:8200`).
- [x] Funnel path handler added (`--set-path=/bardachd`, additive — neighbours
      untouched). Verified live; all neighbour apps confirmed healthy.

## DONE — post-deploy features (Session 03)
- [x] Renamed the app in the UI to **Bàrdachd** (title + brand).
- [x] Added three reference tabs — **Further reading**, **Websites**, **Media** —
      with curated, original-wording content and working links.
- [x] Made those three tabs **user-editable**: add your own items (persisted in
      `poems.db`, new `resources` table) and remove the ones you've added. The
      curated defaults stay built-in and always shown; defaults aren't deletable.
- [x] **PWA**: web manifest + service worker + SVG icons, all prefix-aware, so
      the app installs to a phone/desktop home screen and opens offline.
- [x] Updated `PI-INFRASTRUCTURE.md` (Bàrdachd row; corrected Nature/Skywards;
      noted the dead Ceòl `/`→:8080 502).
- [x] `.gitignore` tidy (`.DS_Store`, `bardachd_patch_*.py`) — files untracked.
- [x] Drift-report habit set up: `drift-report.sh` (FLAT globs) +
      `drift-compare.sh`, both tested; `DRIFT-STEP0-Bardachd.md` captured.
- [x] Session logs written: `SESSION_01.md`, `SESSION_02.md`, `SESSION_03.md`.

## Outstanding — small, at leisure
- [ ] Browser-verify on the phone: open `…/bardachd/`, Add to Home Screen, and
      confirm it launches full-screen with the Bàrdachd icon, scansion/rhyme/
      forms/exercises/save-export work, and the add/remove buttons on the three
      reference tabs work.
- [ ] Remove any leftover test rows added during deploy verification (e.g. the
      "Test" website) via the Remove button in the UI.
- [ ] Drop `PI-INFRASTRUCTURE.md` and `DRIFT-STEP0-Bardachd.md` into the shared
      cross-project docs folder (`~/pi-infrastructure/`-style) — they don't live
      in this repo.
- [ ] (Optional polish) The PWA icons are SVG. iOS home-screen icons are most
      reliable as PNG; if the SVG apple-touch-icon ever looks off on your iPhone,
      swap in a 180×180 and 512×512 PNG. Not needed unless you see a problem.

## Possible later (discussed, not committed)
- [ ] Per-line written-out target for the line being edited (e.g. `da-DUM
      da-DUM…`).
- [ ] Stanza-grouping view (visually break a sonnet into quatrains + couplet).
- These are optional — only if Callum raises them.
