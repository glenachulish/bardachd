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
from fastapi.responses import HTMLResponse
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


@app.get("/api/forms")
def api_forms():
    return FORMS


@app.get("/api/exercises")
def api_exercises():
    return EXERCISES


@app.get("/api/reading")
def api_reading():
    return READING


@app.get("/api/websites")
def api_websites():
    return WEBSITES


@app.get("/api/media")
def api_media():
    return MEDIA


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


from frontend import HTML


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML
