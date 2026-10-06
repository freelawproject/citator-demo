"""Working with the citator pipeline's own output.

The citation extraction and the two-stage treatment classifier produce
free text that the site has to interpret before it can be shown: quotes
that may be fragments of the opinion, authority names with procedural
tags, disposition labels and sentences, court names written in prose, and
several accounts of the decision an opinion reviewed. Everything that
cleans or reconciles that output lives here; the rest of the build treats
the results as data.
"""

from __future__ import annotations

import difflib
import re

from cl_html import TAG_RE, plain_text
from data_source import JsonDict
from taxonomy import SEVERITY_BY_TREATMENT, to_active_voice

# ── Authority names ──────────────────────────────────────────────────────
# A procedural tag the extractor appends to an unnamed order ("Troppi v
# Scarf (leave denied)"). The row shows the case name only; the court,
# date and cite tell the orders apart. Disambiguators naming a distinct
# decision ("(No. 1)", "(Hauck II)") are kept.
ROLE_PARENTHETICAL_RE = re.compile(
    r"\s*\((?:"
    r"cert(?:iorari)?\.?\s*(?:granted|denied|dismissed|grant|denial)|"
    r"leave\s+(?:denied|granted)|lv\.?\s*den\.?|writ\s+(?:denied|refused|granted)|review\s+(?:denied|granted)|"
    r"appeal(?:\s+(?:denied|dismissed|granted))?|rehearing(?:\s+denied)?|probable jurisdiction noted|"
    r"affirmed(?:\s+in\s+part\s+and\s+reversed\s+in\s+part)?|affirmance(?:\s+order)?|aff'?d|"
    r"(?:reversed|rev'?d)(?:\s+on\s+other\s+grounds)?|vacated(?:\s+and\s+remanded)?|modified|remanded|"
    r"order|reargument\s+order|\d{4}|"
    r"on appeal|trial below|trial court|prior round|companion|related|"
    r"court of appeals|state court|district court|lower court|supreme court|"
    r"(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|d\.c\.|federal)\s+circuit"
    r")\)\s*$",
    re.I,
)


def clean_authority_name(name: str) -> str:
    """The case name without the extractor's procedural tag."""
    return ROLE_PARENTHETICAL_RE.sub("", name).strip()


# A case reporter citation: volume, reporter, page ("633 F.3d 894", "4
# Wheat. 316", "263 F. App’x 286"), a slip opinion ("591 U. S. ___"), or
# a short form cut off at "at" ("82 F.4th at", "465 U. S., at").
_REPORTER_CITE_RE = re.compile(
    r"^\d+\s+[A-Za-z(][A-Za-z0-9.'’()&\s-]*?,?\s+(?:\d+|_{2,}|at\b)"
)
# A case's short name standing alone ("Bruton", "Sattar II", "In re
# Google", "NFIB v. OSHA"): one to five words, capitalised apart from the
# connectives, with no digits.
_SHORT_NAME_RE = re.compile(
    r"^(?:[A-Z][A-Za-z'’.&-]*|v\.|re|of|the|In|ex|rel\.)"
    r"(?: (?:[A-Z][A-Za-z'’.&-]*|v\.|re|of|the|ex|rel\.|II|III|IV|V)){0,4}$"
)
_ID_FORM_RE = re.compile(r"^(?:see (?:also )?)?(?:id|ibid)\b|\bsupra\b", re.I)
# Citations that are not to a case: statutes, regulations, session laws,
# public laws and law reviews.
_NON_CASE_CITE_RE = re.compile(
    r"U\. ?S\. ?C\.|§|C\. ?F\. ?R\.|\bStat\.|Fed\. ?Reg\.|Pub\. ?L\."
    r"|L\. ?Rev\.|L\. ?J\.|J\. ?(?:Const|Legal|L)\.|Law Journal",
    re.I,
)


def is_case_group(group: JsonDict) -> bool:
    """Whether a citation group refers to a case. The extraction keeps
    every span the source tagged as a citation, so a group can be a
    statute, a law review article, or a bare "Id." it attached to
    nothing; those have no case name and no case reporter citation."""
    if (group.get("name") or group.get("cl_name") or "").strip():
        return True
    forms = [
        f.strip()
        for f in (group.get("cited_as") or []) + (group.get("citations") or [])
        if not _ID_FORM_RE.search(f)
    ]
    return any(
        (_REPORTER_CITE_RE.match(f) and not _NON_CASE_CITE_RE.search(f))
        or _SHORT_NAME_RE.match(f)
        for f in forms
    )


# ── Dispositions ─────────────────────────────────────────────────────────
# The treatment form of an order the taxonomy has no label for (a motion
# decided, a petition dismissed): a neutral "Ordered" pill with no
# definition, opening the sentence that disposed of the case.
ORDERED_TREATMENT = "Ordered by"
# Labels that record no disposition at all.
_NO_LABEL = frozenset({"", "None", "Other"})


def disposition_treatment(raw: JsonDict | None) -> JsonDict | None:
    """What an opinion did with its case: {"treatment", "severity", "text"}.
    A named appellate disposition is its taxonomy label ("Reversed and
    remanded by") with that treatment's severity and no text; any other
    order, such as a motion decided, is the neutral "Ordered by" and
    carries the sentence that disposed of the case (or the bare label the
    source gave it, such as "Modified"). None when the opinion records
    nothing. The status rows and the History tab both read this."""
    if not raw:
        return None
    label = (raw.get("label") or "").strip()
    text = (raw.get("text") or "").strip()
    treatment = f"{label} by"
    if treatment in SEVERITY_BY_TREATMENT:
        return {
            "treatment": treatment,
            "severity": SEVERITY_BY_TREATMENT[treatment],
            "text": "",
        }
    if text or label not in _NO_LABEL:
        return {
            "treatment": ORDERED_TREATMENT,
            "severity": "Neutral",
            "text": text or label,
        }
    return None


def disposition_label(raw: JsonDict | None) -> JsonDict | None:
    """The disposition for the status rows: a named appellate disposition
    renders as a pill in the active voice, what this opinion did
    ("Affirming", "Reversing and remanding"); any other order as the
    "Ordered" pill, which opens the sentence that disposed of the case."""
    found = disposition_treatment(raw)
    if found is None:
        return None
    return {
        "label": to_active_voice(found["treatment"]),
        "severity": found["severity"],
        "text": found["text"],
    }


# ── Appellate history: the decision below, acts and courts in prose ──────
# Words too common to identify a case by.
_NAME_STOPWORDS = frozenset(
    {
        "v", "vs", "in", "re", "the", "of", "and", "ex", "rel", "et", "al",
        "state", "states", "united", "people", "commonwealth", "inc", "co",
        "corp", "llc", "ltd", "company", "city", "county", "board", "dept",
        "department", "commissioner", "director", "secretary", "estate",
        "matter", "application", "petition", "appeal",
    }
)  # fmt: skip

_CIRCUIT_WORDS: dict[str, str] = {
    "first": "ca1", "second": "ca2", "third": "ca3", "fourth": "ca4",
    "fifth": "ca5", "sixth": "ca6", "seventh": "ca7", "eighth": "ca8",
    "ninth": "ca9", "tenth": "ca10", "eleventh": "ca11", "d.c.": "cadc",
    "d. c.": "cadc", "dc": "cadc", "federal": "cafc",
}  # fmt: skip
_CIRCUIT_RE = re.compile(
    r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth"
    r"|eleventh|d\.\s?c\.|dc|federal)\s+circuit\b"
)
_SCOTUS_RE = re.compile(
    r"(united states|u\.\s?s\.)\s+supreme court"
    r"|supreme court of the united states|\bscotus\b"
)
# A reported act with no opinion behind it is placed from its text.
_SCOTUS_WORDS = (
    "supreme court of the united states",
    "united states supreme court",
)


def _name_words(text: str) -> set[str]:
    return {
        w
        for w in re.findall(r"[a-z]+", (text or "").lower())
        if w not in _NAME_STOPWORDS and len(w) > 2
    }


def below_entry(record: JsonDict) -> JsonDict | None:
    """Which decision below an opinion reviewed, from its own account.

    The account can name several (a companion case, a party, the same
    court twice), so prefer an entry sharing a distinctive word with this
    case's name, then any named entry, then the first.
    """
    entries = [
        e
        for e in (record.get("on_appeal") or [])
        if e.get("court") or e.get("name")
    ]
    if not entries:
        return None
    own = _name_words(record.get("case_name") or "")
    for entry in entries:
        if own & _name_words(entry.get("name") or ""):
            return entry
    for entry in entries:
        if entry.get("name"):
            return entry
    return entries[0]


def act_verbs(label: str) -> frozenset[str]:
    """The acts a direct-history label names, as a set, so two phrasings
    of one event compare equal: "Affirmed in part; Reversed in part" →
    {affirmed, reversed}; "Reversed and remanded" → {reversed, remanded}."""
    words = re.split(r"[;,]|\band\b", label.lower())
    verbs = (w.replace("in part", "").replace("by", "").strip() for w in words)
    return frozenset(v for v in verbs if v)


def names_supreme_court(text: str) -> bool:
    """Whether prose about a court names the U.S. Supreme Court."""
    low = text.lower()
    return any(w in low for w in _SCOTUS_WORDS)


def canonical_court(
    court_display: dict[str, str], text: str
) -> tuple[str, str]:
    """(court id, display name) for a court named in prose, using the
    site's own name when it is a court the site knows."""
    prose = re.sub(r"\s+", " ", text or "").strip()
    low = prose.lower()
    if _SCOTUS_RE.search(low):
        return "scotus", court_display.get(
            "scotus", "Supreme Court of the United States"
        )
    m = _CIRCUIT_RE.search(low)
    if m:
        court_id = _CIRCUIT_WORDS[re.sub(r"\s+", " ", m.group(1))]
        name = court_display.get(court_id) or (
            f"Court of Appeals for the {m.group(1).title()} Circuit"
        )
        return court_id, name
    return "", prose


# ── Quote → enclosing sentence(s) ─────────────────────────────────────────
# A treatment's quote is often a fragment ("cert den 415 US 927; …
# (1974)"). For display and for the in-text jump the site shows the whole
# sentence(s) around it.
_QUOTE_NORM_MAP = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "‚": "'",
        "′": "'",
        "ʹ": "'",
        "ʻ": "'",
        "´": "'",
        "`": "'",
        "“": '"',
        "”": '"',
        "„": '"',
        "″": '"',
        "–": "-",
        "—": "-",
        " ": " ",
    }
)
# Words after which a period does not end a sentence in legal prose.
_ABBREVIATIONS = {
    "v",
    "vs",
    "inc",
    "co",
    "corp",
    "ltd",
    "llc",
    "no",
    "nos",
    "mr",
    "mrs",
    "ms",
    "dr",
    "jr",
    "sr",
    "st",
    "ave",
    "dept",
    "dep't",
    "ass'n",
    "assn",
    "bros",
    "cir",
    "app",
    "div",
    "misc",
    "sup",
    "ct",
    "ed",
    "rev",
    "stat",
    "ann",
    "supp",
    "u.s",
    "s",
    "l",
    "f",
    "p",
    "a",
    "n.e",
    "n.w",
    "s.e",
    "s.w",
    "so",
    "cal",
    "ill",
    "mich",
    "n.y",
    "pa",
    "tex",
    "wash",
    "mass",
    "fla",
    "id",
    "ibid",
    "cf",
    "e.g",
    "i.e",
    "etc",
    "al",
    "supra",
    "infra",
    "art",
    "sec",
    "ch",
    "pt",
    "fed",
    "reg",
    "op",
    "j",
    "jj",
    "c.j",
    "u.s.c",
    "cong",
    "sess",
    "h.r",
    "u",
    "b",
    "d",
    "r",
    "rptr",
    "cal.app",
    "civ",
}
# court and reporter tokens that end in a period inside citations
_CITATION_TOKENS = {
    "miss",
    "ala",
    "ariz",
    "ark",
    "colo",
    "conn",
    "del",
    "ga",
    "haw",
    "ida",
    "ind",
    "kan",
    "ky",
    "la",
    "me",
    "md",
    "minn",
    "mo",
    "mont",
    "neb",
    "nev",
    "okla",
    "or",
    "ore",
    "tenn",
    "vt",
    "va",
    "wis",
    "wyo",
    "n.j",
    "n.m",
    "n.c",
    "n.d",
    "s.c",
    "s.d",
    "e.d",
    "w.d",
    "m.d",
    "c.d",
    "d",
    "bankr",
    "cir",
    "ct",
    "app",
    "supp",
    "misc",
    "rptr",
    "dist",
    "sup",
    "super",
    "surr",
    "fam",
    "crim",
}
_SENTENCE_END_RE = re.compile(r"[.!?][\"'”’)\]]*(?=\s)")


_QUOTE_CHARS = set("\"'‘’‚′ʹʻ´`“”„″")


def _norm_with_map(text: str) -> tuple[str, list[int]]:
    """Normalised text (lower, dashes unified, quotation marks DROPPED — the
    model writes straight quotes where the text has curly ones — single
    spaces) + map from normalised index to original index."""
    out, mp, last_space = [], [], True
    for i, ch in enumerate(text):
        if ch in _QUOTE_CHARS:
            continue
        if ch.isspace() or ch == " ":
            if last_space:
                continue
            out.append(" ")
            mp.append(i)
            last_space = True
        else:
            out.append(ch.translate(_QUOTE_NORM_MAP).lower())
            mp.append(i)
            last_space = False
    return "".join(out), mp


def _norm_quote(quote: str) -> str:
    q, _ = _norm_with_map(quote)
    return q.strip().strip(".,;: ")


def _is_sentence_end(text: str, pos: int) -> bool:
    """Is the terminator ending at `pos` (exclusive) a real sentence end?"""
    # the word before the period
    m = re.search(r"([A-Za-z][\w.'’]*)[.!?][\"'”’)\]]*$", text[:pos])
    after = text[pos:].lstrip()
    if m:
        word = m.group(1).lower().rstrip(".")
        # a bare "Id." / "Ibid." citation sentence ends where a capitalised
        # sentence follows it ("Ibid. That is, …"); "Id. at 405" does not
        if word in ("id", "ibid") and after[:1].isupper():
            return True
        if word in _ABBREVIATIONS or len(word) == 1:  # initials, "J."
            return False
        # an initialism with inner periods ("S.D.", "N.D.", "U.S.", "E.D.")
        # or a court / reporter token inside a citation parenthetical: no
        # sentence ends there, whatever follows
        if "." in word or word in _CITATION_TOKENS:
            return False
    # a period inside a citation ("U. S. 478", "F. 3d") or before a digit
    if not after:
        return True
    if after[0].islower():
        return False
    return not (after[0].isdigit() and text[:pos].rstrip()[-1:] == ".")


def sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """[start, end) of the sentence(s) in `text` covering [start, end)."""
    s = 0
    for m in _SENTENCE_END_RE.finditer(text, 0, start):
        if _is_sentence_end(text, m.end()):
            s = m.end()
    e = len(text)
    # a terminator that is the quote's own last character closes it
    for m in _SENTENCE_END_RE.finditer(text, max(start, end - 1)):
        if _is_sentence_end(text, m.end()):
            e = m.end()
            break
    return s, e


def expand_quote(document: list[dict], quote: str) -> str:
    """The sentence(s) of the opinion containing `quote`, or `quote` itself
    when it cannot be located. Searches every block and footnote of the
    structured document by normalised text; falls back to the quote's
    first 60 / last 40 characters when the model trimmed or altered it."""
    if not quote or isinstance(document, str):
        return quote
    # A quote that skips text with an ellipsis is several passages: widen
    # each part on its own and keep the ellipsis between them.
    parts = [
        p.strip() for p in re.split(r"\s*(?:…|\.\.\.)\s*", quote) if p.strip()
    ]
    if len(parts) > 1 and all(len(p.split()) >= 4 for p in parts):
        return " … ".join(expand_quote(document, p) for p in parts)
    target = _norm_quote(quote)
    if not target:
        return quote
    segments = [
        seg
        for wr in document
        for seg in list(wr.get("blocks", [])) + list(wr.get("footnotes", []))
    ]
    plains = [(plain_text(seg["html"]),) for seg in segments]
    normed = [_norm_with_map(p[0]) for p in plains]
    # 1. the whole quote
    for (plain,), (norm, mp) in zip(plains, normed):
        idx = norm.find(target)
        if idx >= 0:
            return _sentence_at(plain, mp, idx, len(target))
    # 2. the longest run of consecutive quote words found anywhere (the
    #    model trimmed, paraphrased or mis-copied part of it). The run must
    #    be at least eight words AND cover most of the quote, otherwise a
    #    common phrase could land the quote in the wrong sentence — then
    #    the model's own words are shown unchanged.
    words = target.split(" ")
    min_run = max(8, (len(words) + 1) // 2)
    best = (
        None  # (n words, word offset in quote, segment index, norm idx, probe)
    )
    for n in range(len(words), min_run - 1, -1):
        for start in range(0, len(words) - n + 1):
            probe = " ".join(words[start : start + n])
            for k, (norm, _mp) in enumerate(normed):
                idx = norm.find(probe)
                if idx >= 0:
                    best = (n, start, k, idx, probe)
                    break
            if best:
                break
        if best:
            break
    if best:
        n, start, k, idx, probe = best
        plain, (norm, mp) = plains[k][0], normed[k]
        # The anchored run may be only one side of a quote that spans two
        # sentences: widen to the neighbouring sentence when the quote's
        # words on that side are found there.
        lead = words[:start][-6:]
        trail = words[start + n :][:6]
        return _sentence_at(plain, mp, idx, len(probe), lead, trail)
    return quote


def _words_mostly_in(word_list: list[str], text_norm: str) -> bool:
    """At least three of the words, and most of them, occur in the text."""
    words = [w for w in word_list if len(w) > 2]
    if len(words) < 3:
        return False
    hits = sum(1 for w in words if w in text_norm)
    return hits >= 3 and hits * 2 >= len(words)


def _sentence_at(
    plain: str,
    mp: list[int],
    idx: int,
    length: int,
    lead: list[str] | None = None,
    trail: list[str] | None = None,
) -> str:
    s = mp[idx]
    e = mp[idx + length - 1] + 1
    bs, be = sentence_bounds(plain, s, e)
    if lead and bs > 1:
        # look back across up to two very short citation sentences
        # ("Ibid.", "Id., at 405.") to the sentence the quote started in
        probe_end, hops = bs, 0
        while probe_end > 1 and hops < 3:
            prev_s, _ = sentence_bounds(
                plain, max(0, probe_end - 2), max(0, probe_end - 2)
            )
            prev_norm, _ = _norm_with_map(plain[prev_s:probe_end])
            if _words_mostly_in(lead, prev_norm):
                bs = prev_s
                break
            if len(prev_norm.strip()) > 20:
                break
            probe_end, hops = prev_s, hops + 1
    if trail and be < len(plain):
        _, next_e = sentence_bounds(
            plain, min(len(plain), be + 1), min(len(plain), be + 1)
        )
        next_norm, _ = _norm_with_map(plain[be:next_e])
        if _words_mostly_in(trail, next_norm):
            be = next_e
    return plain[bs:be].strip()


# ── Quote verification ────────────────────────────────────────────────
# Is a model-supplied quote actually in the opinion? Compared as word
# tokens (punctuation, spacing and quote styles normalised away), first as
# a whole, then sentence by sentence for quotes stitched from separate
# passages with an ellipsis.
_VERIFY_STAR = re.compile(r"\*\d+")
_VERIFY_NONWORD = re.compile(r"[^a-z0-9]+")


def _verify_tokens(text: str) -> list[str]:
    t = text.translate(_QUOTE_NORM_MAP).lower()
    t = _VERIFY_STAR.sub(" ", t)
    return _VERIFY_NONWORD.sub(" ", t).split()


def document_token_streams(document: list[dict]) -> list[list[str]]:
    """One token stream per writing: its blocks in order, then its footnotes."""
    streams = []
    for wr in document:
        parts = [
            TAG_RE.sub(" ", b.get("html", "")) for b in wr.get("blocks", [])
        ]
        parts += [
            TAG_RE.sub(" ", fn.get("html", ""))
            for fn in wr.get("footnotes", [])
        ]
        streams.append(_verify_tokens(" ".join(parts)))
    return streams


def _coverage(q: list[str], streams: list[list[str]]) -> float:
    """Share of the quote's words found in order at the best-matching place
    in any stream (anchored on the quote's first, middle and last words)."""
    n = len(q)
    if n == 0:
        return 0.0
    best = 0.0
    for st in streams:
        joined = " ".join(st)
        for i in (0, max(0, n // 2), max(0, n - 4)):
            key = " ".join(q[i : i + 4])
            pos = 0
            while True:
                j = joined.find(key, pos)
                if j < 0:
                    break
                off = joined[:j].count(" ") - i
                pos = j + 1
                seg = st[
                    max(0, off - 4) : min(len(st), off + int(n * 1.3) + 8)
                ]
                sm = difflib.SequenceMatcher(None, q, seg, autojunk=False)
                cov = sum(b.size for b in sm.get_matching_blocks()) / n
                if cov > best:
                    best = cov
                if best >= 0.999:
                    return 1.0
    return best


def verify_quote(streams: list[list[str]], quote: str) -> dict:
    """{status, coverage, sentences_found}. status: found | stitched
    (every sentence found, not contiguous) | partial (some sentences) |
    missing | short."""
    q = _verify_tokens(re.sub(r"\s…\s", " ", quote))
    if len(q) < 4:
        return {"status": "short", "coverage": 1.0, "sentences_found": 1.0}
    whole = _coverage(q, streams)
    if whole >= 0.97:
        return {"status": "found", "coverage": whole, "sentences_found": 1.0}
    sents = [
        s
        for s in re.split(r"(?<=[.?!])\s+|\s…\s", quote)
        if len(_verify_tokens(s)) >= 4
    ]
    covs = [_coverage(_verify_tokens(s), streams) for s in sents] or [whole]
    frac = sum(1 for c in covs if c >= 0.9) / len(covs)
    if frac == 1.0:
        status = "stitched"
    elif frac >= 0.5 or whole >= 0.85:
        status = "partial"
    else:
        status = "missing"
    return {"status": status, "coverage": whole, "sentences_found": frac}


def quote_names_case(quote: str, cites: list[str], name: str) -> str:
    """'cite' when a reporter cite of the case is in the quote, 'name' when
    only its short name is, else ''."""
    q = _VERIFY_NONWORD.sub("", quote.translate(_QUOTE_NORM_MAP).lower())
    for c in cites:
        key = _VERIFY_NONWORD.sub("", c.split(",")[0].lower())
        if len(key) >= 5 and key in q:
            return "cite"
    short = re.split(r"\s+v\.?\s+", name or "", maxsplit=1)[0].strip()
    key = _VERIFY_NONWORD.sub("", short.lower())
    if len(key) >= 5 and key[:12] in q:
        return "name"
    return ""
