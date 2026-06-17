# Bàrdachd — Project Notes

_Distilled long-term knowledge for Bàrdachd (the app first drafted under the name
"Prosody"). This is the "why it's built this way" reference — for current
outstanding work see `BARDACHD_TODO.md`; for the operational rules
(deploy, paths, landmines) see `BARDACHD_CLAUDE.md`. Built from the old
`PROSODY_CONTEXT.md`, 17 Jun 2026._

## What it is
A poetry-writing workshop, self-hosted like Ceòl. FastAPI backend, SQLite store,
single-page frontend served at `/` (and, in production, under `/bardachd/`).
Grounded in standard public-domain prosody (metre, rhyme, fixed forms) —
deliberately NOT a reproduction of any copyrighted book's exercises or examples;
all exercise text and form notes are original wording built on public-domain
mechanics.

## Architecture
- `main.py` — FastAPI app: the scansion engine, rhyme/syllable helpers, the form
  library, exercises, target-pattern logic, and all API routes. Serves the UI at
  `/` by importing `HTML` from `frontend.py`.
- `frontend.py` — one big `HTML` string (HTML/CSS/JS) for the whole single-page
  UI. Vanilla JS, no build step.
- `poems.db` — SQLite, created automatically on first run; `db()` context manager
  auto-commits.
- Run: `uvicorn main:app --host 0.0.0.0 --port 8200`.
- Dependencies: `fastapi`, `uvicorn`, `pronouncing`.
- No auth — single-user, private behind Tailscale. Deliberate.

## How the prosody engine works
- Stress and rhyme come from the **CMU pronouncing dictionary** via the
  `pronouncing` library. Each vowel is marked stressed/unstressed.
- **Monosyllables are ambiguous** in English (stress depends on sense/position),
  so they're resolved with a function-word heuristic (articles, prepositions,
  pronouns etc. default to unstressed). This means the metre label is a strong
  hint, not gospel.
- **Unknown words** (names, coinages not in the dictionary) are flagged in the
  readout rather than guessed.
- Metre detection tiles the line with each candidate foot (iamb, trochee,
  anapaest, dactyl, spondee, pyrrhic) and picks the best fit, naming it e.g.
  "iambic pentameter". Verified against known lines: "Tyger Tyger burning bright"
  → trochaic tetrameter; Sonnet 18 opening → iambic pentameter; Byron's "The
  Assyrian came down…" → anapaestic.

## Features
- **Live scansion** — stress dots appear above each syllable as you type.
- **Rhyme finder** — perfect rhymes plus near/slant rhymes (same final vowel,
  different trailing consonants).
- **Form library** — Shakespearean & Petrarchan sonnet, villanelle, ballad,
  haiku, limerick, heroic couplet, quatrain. Each has metre, rhyme map, a note,
  and a "load skeleton" button.
- **Guided exercises** — short ear-training drills (original wording).
- **Save / export** — poems stored on the Pi, exportable as .txt.

## Stress-pattern target overlay
When a fixed form is loaded, each line shows a two-row stress map:
- **Ghost dots** (faint blue, top) = the form's ideal stress pattern for THAT
  line. Per-line, so a limerick's long lines (anapaest×3) and short lines
  (anapaest×2) get different targets.
- **Actual dots** (terracotta, bottom) = your real stresses; red where a stress
  contradicts the metre, amber where the line runs long, hollow where the form
  wants a beat you haven't written.
- **Match badge** = % on-form, plus "N short"/"N over" for syllable-count gaps,
  graded green/amber/red.
- Free verse and haiku show no ghosts (haiku is syllable-count, not stress).
- Backend: `target_lines(form_key)` returns ideal stress strings per line;
  `compare_to_target()` does the per-syllable diff. Blank lines in the draft are
  counted so line N maps to target N.

## Important design stance (don't "fix" this)
Scoring is against STRICT metre on purpose. A skilful, deliberate variation —
e.g. the trochaic first-foot inversion that opens Sonnet 18 — reads as "60% on
form." That's intended: the overlay shows where you depart from the template;
whether a departure is a mistake or a good variation is the writer's judgement. A
red dot is a question ("did I mean that?"), not a verdict. The rules are there to
be felt against, not just obeyed.

## Deployment note (the thing that bites)
In production Bàrdachd is served under a **path prefix** (`/bardachd/`) on the
shared Funnel port 443, not at the root. The backend stays prefix-naïve
(Tailscale strips the prefix) but the **frontend must emit prefix-aware URLs** —
the original Prosody frontend used leading-slash absolute paths everywhere and
would 404 on every API call under the prefix. This must be fixed before first
deploy. Full detail in `BARDACHD_CLAUDE.md` and `PI-INFRASTRUCTURE.md`.

## History
- Drafted and built as "Prosody" (scansion engine + overlay added in two
  passes). Renamed to Bàrdachd 16 Jun 2026.
- Not yet deployed as of 17 Jun 2026 — project knowledge only.

## Possible next steps (discussed, not built)
- Per-line written-out target (e.g. `da-DUM da-DUM…`) for the line being edited.
- Stanza-grouping view (visually break a sonnet into quatrains + couplet).
- Optional; raise only if Callum brings them up.
