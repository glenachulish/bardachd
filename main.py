"""
Prosody — a poetry-writing workshop for ceol-pi.

Grounded in standard public-domain prosody (metre, rhyme, fixed forms).
Single-file FastAPI app. Run with:  uvicorn main:app --host 0.0.0.0 --port 8200

Dependencies:  pip install fastapi uvicorn pronouncing
Data:          poems.db (SQLite, created automatically)
"""

import re
import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager

import pronouncing
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse
from pydantic import BaseModel

DB_PATH = Path(__file__).parent / "poems.db"

app = FastAPI(title="Prosody")


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS poems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT 'Untitled',
                form TEXT NOT NULL DEFAULT 'free',
                body TEXT NOT NULL DEFAULT '',
                created TEXT NOT NULL DEFAULT (datetime('now')),
                updated TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )
        # User-added resources for the Further reading / Websites / Media tabs.
        # The curated lists (READING / WEBSITES / MEDIA below) are built-in and
        # always shown; rows here are the user's own additions, appended after
        # the defaults and individually deletable.
        conn.execute(
            """CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section TEXT NOT NULL,            -- 'reading' | 'websites' | 'media'
                title TEXT NOT NULL DEFAULT '',   -- book title / site name / media name
                detail TEXT NOT NULL DEFAULT '',  -- author (reading) / by (media); blank for websites
                kind TEXT NOT NULL DEFAULT '',    -- e.g. 'Book', 'Podcast', 'Video'; free text
                url TEXT NOT NULL DEFAULT '',     -- link (websites/media); optional for reading
                note TEXT NOT NULL DEFAULT '',    -- why it's useful
                created TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )


init_db()


# --------------------------------------------------------------------------
# Scansion engine
# --------------------------------------------------------------------------
# A foot dictionary keyed by the binary stress string of one foot.
FEET = {
    "01": "iamb",
    "10": "trochee",
    "001": "anapaest",
    "100": "dactyl",
    "11": "spondee",
    "00": "pyrrhic",
}

METRE_NAMES = {
    1: "monometer", 2: "dimeter", 3: "trimeter", 4: "tetrameter",
    5: "pentameter", 6: "hexameter", 7: "heptameter", 8: "octameter",
}


def word_stresses(word):
    """Return a stress string like '010' for a word, or None if unknown.

    CMU marks each vowel 0 (unstressed), 1 (primary) or 2 (secondary).
    We treat 1 and 2 as stressed for scansion purposes. Single-syllable
    words are ambiguous (function words usually unstress) so we mark them
    'x' to be resolved in context.
    """
    clean = re.sub(r"[^a-z']", "", word.lower())
    if not clean:
        return ""
    phones = pronouncing.phones_for_word(clean)
    if not phones:
        return None
    pattern = pronouncing.stresses(phones[0])
    if len(pattern) == 1:
        return "x"  # monosyllable, resolve later
    return "".join("1" if c in "12" else "0" for c in pattern)


# Common monosyllabic function words that are normally unstressed.
WEAK_WORDS = {
    "a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet",
    "of", "to", "in", "on", "at", "by", "as", "is", "was", "be",
    "with", "from", "that", "than", "this", "his", "her", "its",
    "my", "our", "your", "their", "he", "she", "it", "we", "you",
    "i", "am", "are", "were", "do", "did", "has", "had", "have",
    "if", "when", "while", "no", "not",
}


def resolve_monosyllables(tokens, raw):
    """Resolve 'x' marks for monosyllables using a function-word heuristic."""
    out = []
    for stress, word in zip(tokens, raw):
        if stress == "x":
            out.append("0" if word.lower() in WEAK_WORDS else "1")
        else:
            out.append(stress)
    return out


def scan_line(line):
    """Scan a single line. Returns dict with per-syllable stress + analysis."""
    words = re.findall(r"[A-Za-z']+", line)
    syllable_units = []  # list of (word, stress_string_or_None)
    unknown = []
    for w in words:
        s = word_stresses(w)
        if s is None:
            unknown.append(w)
            s = "?"
        syllable_units.append((w, s))

    # Resolve monosyllables in sequence
    resolved = resolve_monosyllables(
        [s if s != "?" else "?" for (_, s) in syllable_units], words
    )

    # Flatten to a syllable-level stress string for the whole line
    flat = []
    syl_words = []
    for (w, _), r in zip(syllable_units, resolved):
        if r == "?":
            flat.append("?")
            syl_words.append(w)
        else:
            for i, ch in enumerate(r):
                flat.append(ch)
                syl_words.append(w if i == 0 else "")
    stress_str = "".join(flat)
    syl_count = len(stress_str)

    detected = detect_metre(stress_str)
    return {
        "line": line,
        "syllables": stress_str,
        "syllable_count": syl_count,
        "syllable_words": syl_words,
        "metre": detected,
        "unknown_words": unknown,
    }


def detect_metre(stress_str):
    """Best-effort foot detection. Tries duple then triple feet."""
    s = stress_str.replace("?", "0")
    if not s:
        return {"foot": None, "feet": 0, "name": "—"}

    # Try to tile the line with a single repeating foot, allowing the
    # final foot to be catalectic (truncated). Score each candidate.
    best = None
    for foot_str, foot_name in FEET.items():
        fl = len(foot_str)
        if fl == 0:
            continue
        matches = 0
        total = 0
        i = 0
        while i < len(s):
            chunk = s[i:i + fl]
            total += 1
            # compare as much as is present
            cmp = foot_str[:len(chunk)]
            if chunk == cmp:
                matches += 1
            i += fl
        score = matches / total if total else 0
        feet = total
        if best is None or score > best["score"]:
            best = {"foot": foot_name, "feet": feet, "score": score,
                    "foot_str": foot_str}

    name = METRE_NAMES.get(best["feet"], f"{best['feet']} feet")
    adjectives = {
        "iamb": "iambic", "trochee": "trochaic", "anapaest": "anapaestic",
        "dactyl": "dactylic", "spondee": "spondaic", "pyrrhic": "pyrrhic",
    }
    adj = adjectives.get(best["foot"], best["foot"])
    label = f"{adj} {name}" if best["foot"] else name
    return {
        "foot": best["foot"],
        "feet": best["feet"],
        "name": label,
        "confidence": round(best["score"], 2),
    }


# --------------------------------------------------------------------------
# Rhyme + syllable helpers
# --------------------------------------------------------------------------
def rhymes_for(word):
    clean = re.sub(r"[^a-z']", "", word.lower())
    if not clean:
        return {"perfect": [], "near": []}
    perfect = pronouncing.rhymes(clean)
    # Near rhymes: same final vowel sound (assonance/slant)
    near = []
    phones = pronouncing.phones_for_word(clean)
    if phones:
        rhyme_part = pronouncing.rhyming_part(phones[0])
        if rhyme_part:
            # The final stressed vowel (with its stress digit), e.g. 'AY1'.
            vowel = rhyme_part.split()[0]
            seen = set(perfect) | {clean}
            # Words whose rhyming part ends on the same vowel sound but
            # differs in the trailing consonants = slant / near rhyme.
            for cand in pronouncing.search(vowel + r"[^ ]* [^ ]+$"):
                if cand not in seen and cand.isalpha():
                    near.append(cand)
                    seen.add(cand)
                if len(near) >= 40:
                    break
            if len(near) < 40:  # also catch vowel-final near rhymes
                for cand in pronouncing.search(vowel + r"$"):
                    if cand not in seen and cand.isalpha():
                        near.append(cand)
                        seen.add(cand)
                    if len(near) >= 40:
                        break
    return {"perfect": perfect[:60], "near": near[:40]}


def syllable_count(word):
    phones = pronouncing.phones_for_word(re.sub(r"[^a-z']", "", word.lower()))
    if not phones:
        return None
    return pronouncing.syllable_count(phones[0])


# --------------------------------------------------------------------------
# Target stress patterns per form
# --------------------------------------------------------------------------
# Foot templates as binary stress strings (0 unstressed, 1 stressed).
FOOT_TEMPLATES = {
    "iamb": "01", "trochee": "10", "anapaest": "001", "dactyl": "100",
}


def build_line(foot, feet, catalectic=False):
    """Return the ideal stress string for one line, e.g. iamb×5 -> '0101010101'.

    catalectic drops the final unstressed syllable (common in trochaic/
    dactylic lines so they can end on a stress).
    """
    pat = FOOT_TEMPLATES[foot] * feet
    if catalectic and pat and pat[-1] == "0":
        pat = pat[:-1]
    return pat


def target_lines(form_key):
    """Return a list of ideal stress strings, one per line of the form.

    None entries mean 'no fixed metre' (e.g. free verse, haiku counts
    syllables rather than stresses)."""
    iamb5 = build_line("iamb", 5)        # 0101010101  (pentameter)
    iamb4 = build_line("iamb", 4)        # 01010101    (tetrameter)
    iamb3 = build_line("iamb", 3)        # 010101      (trimeter)
    anap3 = build_line("anapaest", 3)    # 001001001
    anap2 = build_line("anapaest", 2)    # 001001
    maps = {
        "sonnet-shakespearean": [iamb5] * 14,
        "sonnet-petrarchan": [iamb5] * 14,
        "villanelle": [iamb5] * 19,
        "ballad": [iamb4, iamb3, iamb4, iamb3],
        "limerick": [anap3, anap3, anap2, anap2, anap3],
        "couplet-heroic": [iamb5, iamb5],
        "quatrain": [iamb4, iamb4, iamb4, iamb4],
        # BARDACHD_PATCH_TRIOLET_DETECT_v1
        "triolet": [iamb4] * 8,
        # ADDFORMS_2026 — iambic-pentameter forms added below
        "ottava-rima": [iamb5] * 8,
        "rhyme-royal": [iamb5] * 7,
        "blank-verse": [iamb5] * 10,  # unrhymed iambic pentameter; 10 is a
                                       # starter length, not a fixed limit
        # sestina has no fixed metre (defined by end-words), so no target here
    }
    return maps.get(form_key)


# --------------------------------------------------------------------------
# Form library (public-domain prosodic definitions)
# --------------------------------------------------------------------------
FORMS = {
    "sonnet-shakespearean": {
        "name": "Shakespearean Sonnet",
        "lines": 14,
        "metre": "iambic pentameter (10 syllables, da-DUM ×5)",
        "rhyme": "ABAB CDCD EFEF GG",
        "rhyme_scheme": list("ABABCDCDEFEFGG"),
        "note": "Three quatrains build the argument; the closing couplet turns or resolves it.",
    },
    "sonnet-petrarchan": {
        "name": "Petrarchan Sonnet",
        "lines": 14,
        "metre": "iambic pentameter",
        "rhyme": "ABBAABBA + CDECDE (or CDCDCD)",
        "rhyme_scheme": list("ABBAABBA") + list("CDECDE"),
        "note": "An octave poses a problem; the sestet, after the volta, answers it.",
    },
    "villanelle": {
        "name": "Villanelle",
        "lines": 19,
        "metre": "usually iambic pentameter",
        "rhyme": "ABA ×5 + ABAA; two refrains (A1, A2) alternate and reunite at the close",
        "rhyme_scheme": ["A1","b","A2","a","b","A1","a","b","A2","a","b","A1","a","b","A2","a","b","A1","A2"],
        "note": "Line 1 (A1) and line 3 (A2) recur as refrains. Nineteen lines, five tercets and a quatrain.",
    },
    "ballad": {
        "name": "Ballad Stanza",
        "lines": 4,
        "metre": "alternating iambic tetrameter / trimeter",
        "rhyme": "ABCB (or ABAB)",
        "rhyme_scheme": list("ABCB"),
        "note": "The common metre of hymns and folk song. Repeat the stanza as needed.",
    },
    # BARDACHD_PATCH_TRIOLET_DETECT_v1
    "triolet": {
        "name": "Triolet",
        "lines": 8,
        "metre": "usually iambic tetrameter",
        "rhyme": "ABaAabAB; line 1 returns as 4 and 7, line 2 returns as 8",
        "rhyme_scheme": ["A1","B1","a","A1","a","b","A1","B1"],
        "note": "Eight lines on two rhymes with two refrains. Line 1 recurs as lines 4 and 7; line 2 recurs as line 8.",
    },
    "haiku": {
        "name": "Haiku",
        "lines": 3,
        "metre": "5 / 7 / 5 syllables",
        "rhyme": "none",
        "rhyme_scheme": [],
        "syllable_pattern": [5, 7, 5],
        "note": "A seasonal image and a turn. English haiku often run shorter than 17 syllables.",
    },
    "limerick": {
        "name": "Limerick",
        "lines": 5,
        "metre": "anapaestic; lines 1,2,5 longer, lines 3,4 shorter",
        "rhyme": "AABBA",
        "rhyme_scheme": list("AABBA"),
        "note": "Bouncing anapaests and a punchline. Lines 3 and 4 are a beat shorter.",
    },
    "couplet-heroic": {
        "name": "Heroic Couplet",
        "lines": 2,
        "metre": "iambic pentameter",
        "rhyme": "AA",
        "rhyme_scheme": list("AA"),
        "note": "A self-contained rhymed pair. Chain them for longer argumentative verse.",
    },
    "quatrain": {
        "name": "Quatrain (free metre)",
        "lines": 4,
        "metre": "your choice",
        "rhyme": "ABAB / AABB / ABBA",
        "rhyme_scheme": list("ABAB"),
        "note": "The workhorse stanza. Pick a rhyme scheme and a consistent metre.",
    },
    # ADDFORMS_2026 — four forms added from the essential-forms list
    "ottava-rima": {
        "name": "Ottava Rima",
        "lines": 8,
        "metre": "iambic pentameter",
        "rhyme": "ABABABCC",
        "rhyme_scheme": list("ABABABCC"),
        "note": "An eight-line stanza: six interlocking lines then a clinching "
                "couplet. Long used for narrative, and a fine vehicle for wit.",
    },
    "rhyme-royal": {
        "name": "Rhyme Royal",
        "lines": 7,
        "metre": "iambic pentameter",
        "rhyme": "ABABBCC",
        "rhyme_scheme": list("ABABBCC"),
        "note": "A seven-line stanza with a hinge: the b-rhyme of line 5 looks "
                "back, the couplet then closes. Stately, good for storytelling.",
    },
    "blank-verse": {
        "name": "Blank Verse",
        "lines": 10,
        "metre": "iambic pentameter",
        "rhyme": "none (unrhymed)",
        "rhyme_scheme": [],
        "note": "Unrhymed iambic pentameter — the metre of much verse drama. "
                "No rhyme and no fixed length; the ten lines here are a starting "
                "point. Not to be confused with free verse, which drops the metre too.",
    },
    "sestina": {
        "name": "Sestina",
        "lines": 39,
        "metre": "no fixed metre",
        "rhyme": "none — six repeated end-words, not rhymes",
        "rhyme_scheme": [],
        "note": "Six six-line stanzas and a closing three-line envoi. Six "
                "end-words rotate through a fixed order (6-1-5-2-4-3) each "
                "stanza; the envoi gathers all six. No rhyme, no set metre.",
    },
}


# --------------------------------------------------------------------------
# Form guidance (structure, craft tips, a starter prompt, per-line hints)
# Own wording, generic public-domain prosody. Surfaced when a form is loaded.
# `line_hints` is one short label per line, used to pre-fill the draft with
# guide lines (rhyme letter + role) that the writer types over or clears.
# --------------------------------------------------------------------------
FORM_GUIDANCE = {
    "sonnet-shakespearean": {
        "structure": "14 lines: three quatrains (4+4+4) then a couplet (2).",
        "tips": [
            "Let each quatrain take one step of the thought; save the turn for "
            "the final couplet.",
            "Iambic pentameter is ten syllables, da-DUM ×5 — a gentle first-foot "
            "inversion (DUM-da to open) is a classic, deliberate variation.",
            "Lock the metre first, then reach for the rhyme; the rhyme finder "
            "tab can help once your line-endings are chosen.",
        ],
        "starter": "Try opening on an image you want to argue with — 'They say "
                   "that…' — and spend the quatrains testing it.",
        "line_hints": ["A — quatrain 1", "B", "A", "B",
                       "C — quatrain 2", "D", "C", "D",
                       "E — quatrain 3", "F", "E", "F",
                       "G — couplet (the turn)", "G"],
    },
    "sonnet-petrarchan": {
        "structure": "14 lines: an octave (8) then a sestet (6), with a volta "
                     "(turn) between them.",
        "tips": [
            "Use the octave to pose a problem or question; let the sestet "
            "answer or complicate it after the volta.",
            "The octave's tight ABBAABBA leans on just two rhymes — pick "
            "sounds with plenty of partners (the rhyme finder helps).",
            "The volta is a turn of thought, not just a new stanza — make line "
            "9 feel like a door opening.",
        ],
        "starter": "Pose something unresolved in the octave — a longing, a "
                   "doubt — and let line 9 turn toward it.",
        "line_hints": ["A — octave", "B", "B", "A", "A", "B", "B", "A",
                       "C — sestet (after the volta)", "D", "E", "C", "D", "E"],
    },
    "villanelle": {
        "structure": "19 lines: five tercets (3 each) then a quatrain (4). Two "
                     "refrains — call them A1 (line 1) and A2 (line 3) — return "
                     "in turn and close the poem together.",
        "tips": [
            "Write the two refrains FIRST. They each repeat four times, so "
            "they must be strong, slightly open lines that gather new meaning "
            "on each return.",
            "Refrain pattern: A1 closes tercets 2 and 4; A2 closes tercets 3 "
            "and 5; both close the final quatrain (A1 then A2). The middle "
            "line of every stanza rhymes on b.",
            "Choose refrains that can shift in feeling without changing words — "
            "a line that can be hopeful once and bitter later does the work.",
            "Metre is usually iambic pentameter (da-DUM ×5). Keep the two "
            "refrains exactly the same length so they sit cleanly each time.",
        ],
        "starter": "Draft one haunting, repeatable line for A1 (e.g. a line "
                   "about holding on) and a second for A2 that answers it — "
                   "everything else is built to carry those two back around.",
        "line_hints": [
            "A1 — REFRAIN 1 (write this first)", "b", "A2 — REFRAIN 2 (write this first)",
            "a", "b", "A1 — refrain 1 returns",
            "a", "b", "A2 — refrain 2 returns",
            "a", "b", "A1 — refrain 1 returns",
            "a", "b", "A2 — refrain 2 returns",
            "a", "b", "A1 — refrain 1", "A2 — refrain 2",
        ],
    },
    # BARDACHD_PATCH_TRIOLET_DETECT_v1
    "triolet": {
        "structure": "8 lines, two rhymes (a and b), two refrains. Line 1 (A) returns as lines 4 and 7; line 2 (B) returns as line 8. "
                     "Rhyme: ABaAabAB.",
        "tips": [
            "Write lines 1 and 2 first — they are your two refrains and between them they fill five of the eight lines, so make them strong and a little open.",
            "Only lines 3, 5 and 6 are new: line 3 and 5 rhyme with line 1 (a), line 6 rhymes with line 2 (b). Everything else is a refrain.",
            "Aim for refrains that can shift in sense as the poem turns around them — the pleasure of a triolet is the same words landing differently.",
            "Iambic tetrameter (da-DUM ×4) is the usual measure; keep the two refrains the same length so they recur cleanly.",
        ],
        "starter": "Draft one memorable line for A (returns three times) and one for B (returns twice); the three new lines simply carry them back around.",
        "line_hints": [
            "A — REFRAIN A (line 1; write first)", "B — REFRAIN B (line 2; write first)",
            "a — new, rhymes with A", "A — refrain A returns (= line 1)",
            "a — new, rhymes with A", "b — new, rhymes with B",
            "A — refrain A returns (= line 1)", "B — refrain B returns (= line 2)",
        ],
    },
    "ballad": {
        "structure": "4-line stanza (repeat as many as you like): tetrameter, "
                     "trimeter, tetrameter, trimeter.",
        "tips": [
            "The long/short alternation — 4 beats (8 syllables) then 3 beats "
            "(6 syllables) — is the 'common metre' of hymns and folk song; "
            "read it aloud and you'll feel the swing.",
            "Only lines 2 and 4 need to rhyme (ABCB); that looseness keeps a "
            "narrative moving.",
            "Ballads tell a story — let each stanza advance the action a step.",
        ],
        "starter": "Begin in the middle of an event — 'She rode out at the "
                   "break of day' — and let the stanzas carry it forward.",
        "line_hints": ["A — tetrameter (4 beats)", "B — trimeter (3 beats)",
                       "C — tetrameter (4 beats)", "B — trimeter (3 beats)"],
    },
    "haiku": {
        "structure": "3 lines: 5 / 7 / 5 syllables (English haiku often run "
                     "shorter — aim for brevity over a strict count).",
        "tips": [
            "Pin the poem to a concrete, seasonal image rather than a "
            "statement of feeling.",
            "Aim for a 'cut' — a small turn or surprise between the images, "
            "often after line 2.",
            "No rhyme needed; the music is in the images and the pause.",
        ],
        "starter": "Name one precise thing you can see right now, then let the "
                   "third line turn it somewhere unexpected.",
        "line_hints": ["5 syllables", "7 syllables", "5 syllables"],
    },
    "limerick": {
        "structure": "5 lines: long, long, short, short, long. Bouncing "
                     "anapaests (da-da-DUM).",
        "tips": [
            "Lines 1, 2 and 5 share a rhyme (A) and run long; lines 3 and 4 "
            "share a rhyme (B) and are a beat shorter.",
            "The rhythm is da-da-DUM, da-da-DUM — read aloud to keep it "
            "bouncing rather than forced.",
            "Save the joke or twist for line 5; the short middle lines set it "
            "up.",
        ],
        "starter": "Start with a person and a place that rhyme easily — 'There "
                   "once was a … from …' — and build to a turn in line 5.",
        "line_hints": ["A — long", "A — long", "B — short", "B — short",
                       "A — long (the punchline)"],
    },
    "couplet-heroic": {
        "structure": "2 lines, both iambic pentameter, rhyming AA. Chain many "
                     "for longer verse.",
        "tips": [
            "Aim for a self-contained thought that closes cleanly on the "
            "rhyme — the couplet should feel complete.",
            "Both lines are ten syllables, da-DUM ×5.",
            "A little wit or antithesis between the two lines gives the form "
            "its snap.",
        ],
        "starter": "State a small truth in line 1 and twist or confirm it in "
                   "line 2, landing on the rhyme.",
        "line_hints": ["A — iambic pentameter", "A — iambic pentameter"],
    },
    "quatrain": {
        "structure": "4 lines. Pick a rhyme scheme (ABAB, AABB or ABBA) and a "
                     "metre, and keep both consistent.",
        "tips": [
            "Decide the rhyme scheme before you draft — it changes how the "
            "lines lean on each other.",
            "Hold one metre across all four lines so the stanza feels of a "
            "piece.",
            "A good quatrain often saves a small turn for the last line.",
        ],
        "starter": "Choose ABAB and a single image; let the fourth line turn "
                   "or complete the thought.",
        "line_hints": ["A", "B", "A", "B"],
    },
    # ADDFORMS_2026 — guidance for the four new forms
    "ottava-rima": {
        "structure": "An 8-line stanza: six lines rhyming ABABAB, then a "
                     "couplet CC. All iambic pentameter.",
        "tips": [
            "Let the six alternating lines build the thought, then use the "
            "closing couplet to land it — often with a turn or a wry sting.",
            "Three pairs of A/B rhymes is a lot of repetition — choose sounds "
            "with plenty of partners (the rhyme finder helps).",
            "Every line is ten syllables, da-DUM ×5; keep the couplet as tight "
            "as the rest so it snaps shut.",
        ],
        "starter": "Open a small narrative or argument in the ABABAB lines and "
                   "let the couplet comment on it.",
        "line_hints": ["A — iambic pentameter", "B", "A", "B", "A", "B",
                       "C — couplet (the clincher)", "C"],
    },
    "rhyme-royal": {
        "structure": "A 7-line stanza in iambic pentameter, rhyming ABABBCC.",
        "tips": [
            "The shared b-rhyme on lines 4 and 5 is the hinge — it links the "
            "opening quatrain to the closing couplet.",
            "Use the final couplet (CC) to resolve or turn the stanza.",
            "Every line is ten syllables, da-DUM ×5.",
        ],
        "starter": "Set something going in the first four lines, pivot on the "
                   "b-rhyme, and close on the couplet.",
        "line_hints": ["A — iambic pentameter", "B", "A", "B",
                       "B — the hinge", "C — couplet", "C"],
    },
    "blank-verse": {
        "structure": "Unrhymed iambic pentameter. No rhyme, no fixed length — "
                     "ten lines here are just a starting point; add or remove "
                     "as the poem needs.",
        "tips": [
            "Every line is ten syllables, da-DUM ×5 — the overlay checks the "
            "metre; there is nothing to rhyme.",
            "Because there's no rhyme to lean on, let the metre and the "
            "line-endings (enjambment) do the shaping.",
            "Don't confuse it with free verse: blank verse keeps the strict "
            "iambic beat.",
        ],
        "starter": "Speak plainly in a steady five-beat line — blank verse is "
                   "closest to natural English speech; follow a thought across "
                   "several lines.",
        "line_hints": ["iambic pentameter", "iambic pentameter",
                       "iambic pentameter", "iambic pentameter",
                       "iambic pentameter", "iambic pentameter",
                       "iambic pentameter", "iambic pentameter",
                       "iambic pentameter", "iambic pentameter"],
    },
    "sestina": {
        "structure": "Six 6-line stanzas then a 3-line envoi (39 lines). The "
                     "six end-words of stanza 1 return as the end-words of "
                     "every stanza, in a fixed rotating order; the envoi uses "
                     "all six.",
        "tips": [
            "Choose your six end-words first, and choose them well — they "
            "carry the whole poem and should be words that can shift in sense "
            "(e.g. 'light', 'turn', 'fall').",
            "The rotation is 6-1-5-2-4-3: each stanza takes the previous "
            "stanza's end-words in that order. The guide lines below number "
            "the end-word (1–6) for every line so you can see the pattern.",
            "There is no rhyme and no fixed metre — the discipline is entirely "
            "in the repeating words. The envoi packs two end-words into each "
            "of its three lines.",
        ],
        "starter": "Pick six everyday but flexible nouns, set them as the "
                   "end-words of the first stanza, then let the rotation pull "
                   "the poem somewhere you didn't plan.",
        "line_hints": ["end-word 1 (stanza 1)", "end-word 2", "end-word 3", "end-word 4", "end-word 5", "end-word 6",
                       "end-word 6 (stanza 2)", "end-word 1", "end-word 5", "end-word 2", "end-word 4", "end-word 3",
                       "end-word 3 (stanza 3)", "end-word 6", "end-word 4", "end-word 1", "end-word 2", "end-word 5",
                       "end-word 5 (stanza 4)", "end-word 3", "end-word 2", "end-word 6", "end-word 1", "end-word 4",
                       "end-word 4 (stanza 5)", "end-word 5", "end-word 1", "end-word 3", "end-word 6", "end-word 2",
                       "end-word 2 (stanza 6)", "end-word 4", "end-word 6", "end-word 5", "end-word 3", "end-word 1",
                       "envoi: ends on 5 (2 mid-line)", "envoi: ends on 3 (4 mid-line)", "envoi: ends on 1 (6 mid-line)"],
    },
}

# Guided exercises, structured by skill (own wording, generic prosody).
EXERCISES = [
    {"id": "ear-1", "skill": "The ear",
     "title": "Hear the heartbeat",
     "brief": "Write four lines of strict iambic pentameter on any subject. "
              "Don't worry about rhyme. Just feel the da-DUM da-DUM ×5 and "
              "let the scansion checker confirm each line lands on ten."},
    {"id": "ear-2", "skill": "The ear",
     "title": "Switch the metre",
     "brief": "Take a single sentence and write it twice: once in iambs "
              "(rising) and once in trochees (falling). Notice how the mood "
              "changes when the stress leads."},
    {"id": "rhyme-1", "skill": "Rhyme",
     "title": "Perfect vs slant",
     "brief": "Pick an end-word, fetch its rhymes, and write a couplet using "
              "a perfect rhyme. Then rewrite it using a near (slant) rhyme. "
              "Which feels more surprising?"},
    {"id": "form-1", "skill": "Form",
     "title": "First quatrain",
     "brief": "Write one ABAB quatrain in iambic tetrameter. Lock the metre "
              "first, then find the rhymes — not the other way round."},
    {"id": "form-2", "skill": "Form",
     "title": "Build a refrain",
     "brief": "Draft the two refrain lines of a villanelle (A1 and A2) before "
              "anything else. They must be strong enough to bear five and "
              "four repetitions respectively."},
    {"id": "play-1", "skill": "Play",
     "title": "A clean limerick",
     "brief": "Write a limerick with genuine anapaests. The bounce only works "
              "if the rhythm is da-da-DUM, not forced. Read it aloud."},
]


# --------------------------------------------------------------------------
# Further reading — books on prosody, metre and form (own descriptions)
# --------------------------------------------------------------------------
READING = [
    {"title": "Poetic Meter and Poetic Form", "author": "Paul Fussell",
     "kind": "Classic study",
     "note": "The standard text on English metre and the fixed forms. Clear, "
             "opinionated, and full of worked scansions — the obvious first "
             "stop for understanding how feet and lines actually behave."},
    {"title": "A Poetry Handbook", "author": "Mary Oliver",
     "kind": "Practical guide",
     "note": "A short, warm introduction to sound, line and metre from a poet "
             "who teaches by ear. Good for building intuition before theory."},
    {"title": "The Ode Less Travelled", "author": "Stephen Fry",
     "kind": "Hands-on course",
     "note": "A genial, exercise-driven walk through metre, rhyme and form. "
             "Written for people who want to *write* in form, with drills much "
             "like the ones in the Exercises tab."},
    {"title": "Rhyme's Reason", "author": "John Hollander",
     "kind": "Verse-form primer",
     "note": "A famously compact guide that demonstrates each form in verse "
             "that describes itself — the definition and the example are the "
             "same lines. Delightful and genuinely instructive."},
    {"title": "The Making of a Poem", "author": "Strand & Boland (eds.)",
     "kind": "Form anthology",
     "note": "An anthology arranged by form: sonnet, villanelle, sestina and "
             "the rest, each with a short introduction and strong examples. "
             "Useful for hearing a form done well, many times over."},
    {"title": "All the Fun's in How You Say a Thing", "author": "Timothy Steele",
     "kind": "Versification study",
     "note": "A lucid, thorough account of how metre meets natural speech — "
             "why a line scans as it does and how variation creates effect. "
             "Pairs well with the strict-metre scoring this app uses."},
    {"title": "Patterns of Poetry", "author": "Miller Williams",
     "kind": "Form reference",
     "note": "A compact, practical catalogue of traditional fixed forms with "
             "examples — handy as a bench reference when you want to try one."},
]


# --------------------------------------------------------------------------
# Useful websites (own descriptions)
# --------------------------------------------------------------------------
WEBSITES = [
    {"name": "Poetry Foundation — Glossary of Poetic Terms",
     "url": "https://www.poetryfoundation.org/learn/glossary-terms",
     "note": "A searchable glossary of forms, metre and technique, each term "
             "linked to real poems that use it. The best free reference for "
             "the vocabulary behind scansion."},
    {"name": "Poetry Foundation — Learn",
     "url": "https://www.poetryfoundation.org/learn",
     "note": "Essays, poem guides and reading material on craft and form, "
             "alongside an enormous archive of poems to read aloud."},
    {"name": "Academy of American Poets (poets.org)",
     "url": "https://poets.org/glossary",
     "note": "Glossary, form descriptions and a large poem archive. Its "
             "'poetic forms' pages give concise definitions of the sonnet, "
             "villanelle, ballad and more."},
    {"name": "The Poetry Archive",
     "url": "https://poetryarchive.org",
     "note": "Recordings of poets reading their own work — the single best "
             "way to train your ear for metre and line, since you hear where "
             "the stresses really fall."},
    {"name": "Representative Poetry Online (Univ. of Toronto)",
     "url": "https://rpo.library.utoronto.ca",
     "note": "A scholarly, public collection of poetry from Old English to "
             "now, with a glossary and timeline. Good for tracing how a form "
             "developed over centuries."},
    {"name": "The Poetry Society (UK)",
     "url": "https://poetrysociety.org.uk",
     "note": "A UK home for poets: competitions, prompts, and resources, plus "
             "the long-running Poetry Review."},
]


# --------------------------------------------------------------------------
# Media — videos and podcasts (own descriptions)
# --------------------------------------------------------------------------
MEDIA = [
    {"kind": "Podcast", "name": "Poetry Off the Shelf",
     "by": "Poetry Foundation",
     "url": "https://www.poetryfoundation.org/podcasts/off-the-shelf",
     "note": "In-depth conversations on contemporary poetry and the writing "
             "process — a window into how working poets think about craft."},
    {"kind": "Podcast", "name": "The Slowdown",
     "by": "Originally Tracy K. Smith / Major Jackson",
     "url": "https://www.slowdownshow.org",
     "note": "A short daily episode: one poem, read and briefly reflected on. "
             "An easy habit for hearing a poem a day and feeling its rhythm."},
    {"kind": "Podcast", "name": "Poetry Unbound",
     "by": "Pádraig Ó Tuama (On Being)",
     "url": "https://onbeing.org/series/poetry-unbound/",
     "note": "Each short episode walks slowly through a single poem. Excellent "
             "for learning to read closely and notice how line and sound work."},
    {"kind": "Podcast", "name": "The Poetry Magazine Podcast",
     "by": "Poetry Foundation",
     "url": "https://www.poetryfoundation.org/podcasts/the-poetry-magazine-podcast",
     "note": "Poets read and discuss their own work, giving an unguarded look "
             "at choices of form, line and sound."},
    {"kind": "Video", "name": "Poetry Foundation video archive",
     "by": "Poetry Foundation",
     "url": "https://www.poetryfoundation.org/videos",
     "note": "Readings, interviews and short poetry documentaries — good for "
             "watching poets perform their work and hearing the metre live."},
    {"kind": "Video", "name": "The Poetry Archive (audio/video readings)",
     "by": "Poetry Archive",
     "url": "https://poetryarchive.org",
     "note": "A vast collection of poets reading aloud. Listening alongside the "
             "text on the page is the fastest way to train your ear for stress."},
]


# --------------------------------------------------------------------------
# API models
# --------------------------------------------------------------------------
class ScanRequest(BaseModel):
    text: str
    form: str = "free"


class PoemIn(BaseModel):
    title: str = "Untitled"
    form: str = "free"
    body: str = ""


class ResourceIn(BaseModel):
    title: str = ""      # book title / site name / media name
    detail: str = ""     # author (reading) / by (media)
    kind: str = ""       # e.g. Book / Podcast / Video (free text)
    url: str = ""        # link
    note: str = ""       # why it's useful


# --------------------------------------------------------------------------
# API routes
# --------------------------------------------------------------------------
@app.post("/api/scan")
def api_scan(req: ScanRequest):
    targets = target_lines(req.form)  # list or None
    raw_lines = req.text.splitlines()
    out = []
    line_index = 0  # index into the form's target list (counts all lines)
    for ln in raw_lines:
        if not ln.strip():
            line_index += 1
            continue
        scanned = scan_line(ln)
        target = None
        if targets and line_index < len(targets):
            target = targets[line_index]
        if target:
            scanned["target"] = target
            scanned["diff"] = compare_to_target(scanned["syllables"], target)
        line_index += 1
        out.append(scanned)
    return {"lines": out, "has_target": bool(targets)}


def compare_to_target(actual, target):
    """Per-syllable comparison of actual vs ideal stress.

    Returns a list of 'ok' / 'off' / 'extra' / 'missing' the length of the
    longer of the two, plus a simple match ratio. '?' (unknown) never counts
    as wrong — those syllables are marked 'ok' so dictionary gaps don't
    penalise the reading."""
    marks = []
    n = max(len(actual), len(target))
    hits = comparable = 0
    for i in range(n):
        a = actual[i] if i < len(actual) else None
        t = target[i] if i < len(target) else None
        if a is None:
            marks.append("missing")          # line is short of the metre
        elif t is None:
            marks.append("extra")            # line runs long
        elif a == "?":
            marks.append("ok")               # unknown word, don't judge
        else:
            comparable += 1
            if a == t:
                hits += 1
                marks.append("ok")
            else:
                marks.append("off")
    ratio = round(hits / comparable, 2) if comparable else None
    return {"marks": marks, "match": ratio,
            "syllable_gap": len(actual) - len(target)}


@app.get("/api/rhymes/{word}")
def api_rhymes(word: str):
    return rhymes_for(word)


@app.get("/api/syllables/{word}")
def api_syllables(word: str):
    n = syllable_count(word)
    return {"word": word, "syllables": n}


# BARDACHD_PATCH_LINE_TARGETS_v1: per-line beats+syllables for the editor labels.
def _line_targets(key):
    """One {'beats','syllables'} per line. From the metrical target where
    there is one; from syllable_pattern (beats=None) for syllable-counted
    forms like haiku; empty when the form has no fixed line shape."""
    tgt = target_lines(key)
    if tgt:
        res = []
        for s in tgt:
            if s is None:
                res.append({"beats": None, "syllables": None})
            else:
                res.append({"beats": s.count("1"), "syllables": len(s)})
        return res
    pat = FORMS.get(key, {}).get("syllable_pattern")
    if pat:
        return [{"beats": None, "syllables": int(n)} for n in pat]
    return []

@app.get("/api/forms")
def api_forms():
    # Merge in guidance (structure, tips, starter prompt, per-line hints) so
    # the editor can show it when a form is loaded. Existing fields unchanged.
    out = {}
    for k, v in FORMS.items():
        item = dict(v)
        if k in FORM_GUIDANCE:
            item["guidance"] = FORM_GUIDANCE[k]
        item["line_targets"] = _line_targets(k)
        out[k] = item
    return out


@app.get("/api/exercises")
def api_exercises():
    return EXERCISES


def _user_resources(section):
    """User-added rows for a section, shaped to match the section's default
    item keys so the frontend can render them identically. Each carries
    builtin=False and an id so the UI can offer a delete button."""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM resources WHERE section=? ORDER BY created ASC",
            (section,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if section == "reading":
            item = {"title": d["title"], "author": d["detail"],
                    "kind": d["kind"] or "Added", "note": d["note"]}
            if d["url"]:
                item["url"] = d["url"]
        elif section == "websites":
            item = {"name": d["title"], "url": d["url"], "note": d["note"]}
        else:  # media
            item = {"kind": d["kind"] or "Added", "name": d["title"],
                    "by": d["detail"], "url": d["url"], "note": d["note"]}
        item["id"] = d["id"]
        item["builtin"] = False
        out.append(item)
    return out


def _with_builtin_flag(items):
    """Tag the curated defaults so the frontend knows they aren't deletable."""
    out = []
    for it in items:
        c = dict(it)
        c["builtin"] = True
        out.append(c)
    return out


@app.get("/api/reading")
def api_reading():
    return _with_builtin_flag(READING) + _user_resources("reading")


@app.get("/api/websites")
def api_websites():
    return _with_builtin_flag(WEBSITES) + _user_resources("websites")


@app.get("/api/media")
def api_media():
    return _with_builtin_flag(MEDIA) + _user_resources("media")


_VALID_SECTIONS = {"reading", "websites", "media"}


@app.post("/api/resources/{section}")
def api_add_resource(section: str, r: "ResourceIn"):
    if section not in _VALID_SECTIONS:
        raise HTTPException(404, "Unknown section")
    if not r.title.strip():
        raise HTTPException(400, "Title/name is required")
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO resources (section,title,detail,kind,url,note)
               VALUES (?,?,?,?,?,?)""",
            (section, r.title.strip(), r.detail.strip(), r.kind.strip(),
             r.url.strip(), r.note.strip()),
        )
        return {"id": cur.lastrowid}


@app.delete("/api/resources/{section}/{rid}")
def api_delete_resource(section: str, rid: int):
    if section not in _VALID_SECTIONS:
        raise HTTPException(404, "Unknown section")
    with db() as conn:
        conn.execute(
            "DELETE FROM resources WHERE id=? AND section=?", (rid, section)
        )
    return {"ok": True}


@app.get("/api/poems")
def api_list_poems():
    with db() as conn:
        rows = conn.execute(
            "SELECT id,title,form,updated FROM poems ORDER BY updated DESC"
        ).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/poems/{pid}")
def api_get_poem(pid: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM poems WHERE id=?", (pid,)).fetchone()
        if not row:
            raise HTTPException(404, "Poem not found")
        return dict(row)


@app.post("/api/poems")
def api_create_poem(p: PoemIn):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO poems (title,form,body) VALUES (?,?,?)",
            (p.title, p.form, p.body),
        )
        return {"id": cur.lastrowid}


@app.put("/api/poems/{pid}")
def api_update_poem(pid: int, p: PoemIn):
    with db() as conn:
        conn.execute(
            "UPDATE poems SET title=?,form=?,body=?,updated=datetime('now') WHERE id=?",
            (p.title, p.form, p.body, pid),
        )
    return {"ok": True}


@app.delete("/api/poems/{pid}")
def api_delete_poem(pid: int):
    with db() as conn:
        conn.execute("DELETE FROM poems WHERE id=?", (pid,))
    return {"ok": True}


@app.get("/api/poems/{pid}/export")
def api_export_poem(pid: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM poems WHERE id=?", (pid,)).fetchone()
        if not row:
            raise HTTPException(404, "Poem not found")
        d = dict(row)
    text = f"{d['title']}\n{'=' * len(d['title'])}\n\n{d['body']}\n\n— form: {d['form']}\n"
    return {"filename": f"{d['title']}.txt", "content": text}


# --------------------------------------------------------------------------
# BARDACHD_PATCH_TRIOLET_DETECT_v1: form detection for existing poems
# --------------------------------------------------------------------------
def _rhyme_signature(lines):
    """Map each non-blank line to a rhyme-class letter based on its last
    word's rhyming part. Lines that don't rhyme with anything earlier get
    a fresh letter. Unknown words get their own class."""
    import string
    classes = []          # list of rhyming_part strings, index = class id
    sig = []
    for ln in lines:
        words = re.findall(r"[A-Za-z']+", ln)
        if not words:
            continue
        last = re.sub(r"[^a-z']", "", words[-1].lower())
        phones = pronouncing.phones_for_word(last) if last else []
        part = pronouncing.rhyming_part(phones[0]) if phones else None
        cid = None
        if part is not None:
            for i, p in enumerate(classes):
                if p == part:
                    cid = i
                    break
        if cid is None:
            cid = len(classes)
            classes.append(part if part is not None else object())
        sig.append(cid)
    return sig

def _scheme_to_ids(scheme):
    """Normalise a form's rhyme_scheme (e.g. ['A1','b','A2',...] or
    list('ABCB')) to integer classes by base letter, refrains included."""
    ids = []
    seen = {}
    for tok in scheme:
        key = tok[0].lower()  # base rhyme letter; A1/A2 share 'a'
        if key not in seen:
            seen[key] = len(seen)
        ids.append(seen[key])
    return ids

def _sig_similarity(a, b):
    """Fraction of line-pairs whose 'same-rhyme-or-not' relation agrees
    between two equal-length signatures. Order-independent of letter names."""
    n = len(a)
    if n < 2:
        return 0.0
    agree = 0
    total = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += 1
            if (a[i] == a[j]) == (b[i] == b[j]):
                agree += 1
    return agree / total if total else 0.0

def detect_form(body):
    """Score the poem against every form; return best guess + confidence."""
    lines = [ln for ln in body.splitlines() if ln.strip()]
    n = len(lines)
    if n < 2:
        return {"form": "free", "name": "Free verse", "confidence": "low",
                "score": 0.0, "reason": "Too short to match a fixed form."}
    poem_sig = _rhyme_signature(lines)
    syl_counts = [scan_line(ln)["syllable_count"] for ln in lines]

    # Rhyme density: fraction of lines that actually share a rhyme class
    # with at least one other line. Near zero ⇒ the poem doesn't really
    # rhyme, so we must not reward it for incidentally agreeing with a
    # rhymed scheme's 'these two lines DON'T rhyme' relations.
    from collections import Counter
    counts = Counter(poem_sig)
    rhymed_lines = sum(1 for cid in poem_sig if counts[cid] >= 2)
    rhyme_density = rhymed_lines / len(poem_sig) if poem_sig else 0.0

    best = None
    for key, v in FORMS.items():
        flines = v.get("lines")
        scheme = v.get("rhyme_scheme")
        # An unrhymed form (e.g. blank verse) has all-distinct scheme
        # letters, so it expects no rhyming pairs.
        unrhymed_form = bool(scheme) and len(set(s[0].lower() for s in scheme)) == len(scheme)
        # ---- line-count score (strong) -------------------------------
        if not flines:
            lc = 0.0
        elif n == flines:
            lc = 1.0
        elif flines and n % flines == 0:
            lc = 0.7   # whole number of stanzas (e.g. repeated quatrains)
        else:
            lc = max(0.0, 1.0 - abs(n - flines) / max(flines, n))
        # ---- rhyme score (strong) ------------------------------------
        rs = 0.0
        if scheme and len(scheme) == n:
            rs = _sig_similarity(poem_sig, _scheme_to_ids(scheme))
        elif scheme and flines and n % flines == 0:
            # compare stanza-by-stanza against the repeating unit
            unit = _scheme_to_ids(scheme)
            parts = []
            for s in range(0, n, flines):
                parts.append(_sig_similarity(poem_sig[s:s + flines], unit))
            rs = sum(parts) / len(parts) if parts else 0.0
        # A poem that essentially doesn't rhyme should not score well
        # against a RHYMED form; fade rhyme credit toward zero. Unrhymed
        # forms (blank verse) are unaffected.
        if not unrhymed_form and rhyme_density < 0.34:
            rs *= rhyme_density / 0.34
        # ---- metre score (soft tiebreaker) ---------------------------
        tgt = target_lines(key)
        ms = 0.0
        if tgt and len(tgt) == n:
            agree = 0
            for got, want in zip(syl_counts, (len(t) for t in tgt)):
                if got == want:
                    agree += 1
            ms = agree / n
        # ---- weighted total ------------------------------------------
        score = 0.45 * lc + 0.45 * rs + 0.10 * ms
        if best is None or score > best["score"]:
            best = {"form": key, "name": v.get("name", key),
                    "score": round(score, 3), "lc": lc, "rs": rs, "ms": ms}

    if not best or best["score"] < 0.55:
        return {"form": "free", "name": "Free verse",
                "confidence": "low", "score": round(best["score"], 3) if best else 0.0,
                "reason": "No fixed form fits closely — reads as free verse."}
    band = "high" if best["score"] >= 0.8 else "medium" if best["score"] >= 0.65 else "low"
    bits = []
    bits.append("line count matches" if best["lc"] >= 0.99 else
                ("line count is a multiple" if best["lc"] >= 0.7 else "line count is close"))
    if best["rs"] >= 0.85:
        bits.append("rhyme pattern fits well")
    elif best["rs"] >= 0.6:
        bits.append("rhyme pattern roughly fits")
    reason = "; ".join(bits) + "." if bits else "closest overall match."
    return {"form": best["form"], "name": best["name"],
            "confidence": band, "score": best["score"], "reason": reason}

class DetectRequest(BaseModel):
    body: str

@app.post("/api/detect-form")
def api_detect_form(req: DetectRequest):
    return detect_form(req.body or "")


import hashlib
from frontend import HTML


# --------------------------------------------------------------------------
# PWA: manifest, service worker, and icon
# --------------------------------------------------------------------------
# All URLs here are RELATIVE so they resolve correctly whether the app is
# served at "/" (local dev) or under "/bardachd/" (production behind the
# Tailscale path prefix). The browser resolves "." and "icon.svg" against the
# document/manifest location, so no absolute paths are baked in.

MANIFEST = {
    "name": "Bàrdachd — metre & rhyme",
    "short_name": "Bàrdachd",
    "description": "A workshop in metre and rhyme: scansion, rhyme, forms.",
    "start_url": ".",
    "scope": ".",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#f3efe3",
    "theme_color": "#2f4a6b",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png",
         "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png",
         "purpose": "any"},
        {"src": "icon-maskable-512.png", "sizes": "512x512",
         "type": "image/png", "purpose": "maskable"},
        {"src": "icon.svg", "sizes": "any", "type": "image/svg+xml",
         "purpose": "any"},
    ],
}

# A simple, dependency-free icon: a "B" on the app's deep-blue ground, drawn in
# the paper/terracotta palette. SVG scales to any launcher size.
_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" rx="96" fill="#2f4a6b"/>
<text x="50%" y="52%" dy=".35em" text-anchor="middle"
 font-family="Iowan Old Style,Palatino,Georgia,serif" font-size="300"
 font-weight="600" fill="#f3efe3">B</text>
<circle cx="256" cy="430" r="20" fill="#9a5b3b"/>
</svg>"""

# Maskable variant: same mark but with safe-zone padding so launchers that
# crop to a circle/squircle don't clip the letter.
_ICON_MASKABLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" fill="#2f4a6b"/>
<text x="50%" y="50%" dy=".35em" text-anchor="middle"
 font-family="Iowan Old Style,Palatino,Georgia,serif" font-size="230"
 font-weight="600" fill="#f3efe3">B</text>
</svg>"""

# Service worker: caches the app shell so it opens offline and feels app-like.
# Network-first for API calls (so data stays fresh), cache-first for the shell.
# BARDACHD_PATCH_SW_AUTOUPDATE_v1: cache name tracks a content hash of the shell, so each
# deploy invalidates the old cache; the shell is served network-first so
# updates arrive on next launch instead of being pinned.
_SHELL_HASH = hashlib.sha1(HTML.encode('utf-8')).hexdigest()[:8]
_SW_JS = "const CACHE='bardachd-" + _SHELL_HASH + "';\n" + """
const SHELL=['./','./manifest.webmanifest','./icon.svg','./icon-180.png','./icon-192.png'];
const SHELL_PATHS=new Set(['', '/', 'index.html']);
self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(
    ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',e=>{
  const req=e.request;
  if(req.method!=='GET'){return;}
  const url=new URL(req.url);
  // API calls: network-first, fall back to cache only if offline.
  if(url.pathname.includes('/api/')){
    e.respondWith(fetch(req).catch(()=>caches.match(req)));
    return;
  }
  // App shell (the HTML/JS document): NETWORK-FIRST so a deploy shows up
  // on next launch. Fall back to cache when offline.
  const isShell = req.mode==='navigate' ||
    url.pathname.endsWith('/') || url.pathname.endsWith('/index.html');
  if(isShell){
    e.respondWith(
      fetch(req).then(res=>{
        const copy=res.clone();
        caches.open(CACHE).then(c=>c.put(req,copy));
        return res;
      }).catch(()=>caches.match(req).then(h=>h||caches.match('./')))
    );
    return;
  }
  // Other assets (icons, manifest): cache-first, refresh in background.
  e.respondWith(caches.match(req).then(hit=>hit||fetch(req).then(res=>{
    const copy=res.clone();
    caches.open(CACHE).then(c=>c.put(req,copy));
    return res;
  }).catch(()=>caches.match('./'))));
});
"""


@app.get("/manifest.webmanifest")
def manifest():
    return JSONResponse(MANIFEST, media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    # Service workers must be served with a JS content type and no long cache.
    return Response(_SW_JS, media_type="application/javascript",
                    headers={"Cache-Control": "no-cache"})


@app.get("/icon.svg")
def icon_svg():
    return Response(_ICON_SVG, media_type="image/svg+xml")


@app.get("/icon-maskable.svg")
def icon_maskable_svg():
    return Response(_ICON_MASKABLE_SVG, media_type="image/svg+xml")


# PNG icons (served from disk beside main.py). iOS Safari is unreliable with
# SVG home-screen icons, so the apple-touch-icon and the manifest point at
# these PNGs; the SVG remains as a scalable fallback for browsers that prefer
# it. Files: icon-180.png, icon-192.png, icon-512.png, icon-maskable-512.png.
_ICON_DIR = Path(__file__).parent
_ALLOWED_PNG = {
    "icon-180.png", "icon-192.png", "icon-512.png", "icon-maskable-512.png",
}


@app.get("/{name}.png")
def icon_png(name: str):
    fn = f"{name}.png"
    if fn not in _ALLOWED_PNG:
        raise HTTPException(404, "Not found")
    p = _ICON_DIR / fn
    if not p.exists():
        raise HTTPException(404, "Not found")
    return Response(p.read_bytes(), media_type="image/png",
                    headers={"Cache-Control": "max-age=86400"})


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML
