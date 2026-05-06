"""Transforms mock fixtures (or, eventually, real inference output) into the
Eleventy data contract documented in
ai-research/citator_launch_plan/demo_site_design.md § Data contract.

Outputs:
    _data/opinions/{cluster_id}.json   one per scoped opinion
    _data/index.json                    global listing for Search Results

Real-data swap (issue #13) replaces the import below with a function that
reads CSVs from data-source/.
"""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

from mock_data import (
    COURT_DISPLAY,
    MOCK_OPINIONS,
    SCOPED_CLUSTER_IDS,
)

# ── Canonical severity map ─────────────────────────────────────────────
SEVERITY_BY_TREATMENT = {
    # Stop
    "Reversed by": "Stop",
    "Reversed and remanded by": "Stop",
    "Vacated by": "Stop",
    "Vacated and remanded by": "Stop",
    "Overruled by": "Stop",
    "Abrogated by": "Stop",
    "Questioned by": "Stop",
    # Warning
    "Affirmed in part; Reversed in part by": "Warning",
    "Affirmed in part; Vacated in part by": "Warning",
    "Disapproved by": "Warning",
    "Limited by": "Warning",
    # Caution
    "Remanded by": "Caution",
    "Cert. granted by": "Caution",
    "Criticized by": "Caution",
    "Distinguished by": "Caution",
    "Declined to follow by": "Caution",
    # Neutral
    "Dismissed by": "Neutral",
    "Affirmed by": "Neutral",
    "Cert. denied by": "Neutral",
    "Cited by": "Neutral",
}

SEVERITY_RANK = {
    "Stop": 0,
    "Warning": 1,
    "Caution": 2,
    "Related": 3,
    "Neutral": 4,
}
NEGATIVE_TIERS = {"Stop", "Warning", "Caution"}

OUT_DIR = Path(__file__).parent.parent / "_data"
OPINIONS_OUT = OUT_DIR / "opinions"


def severity_for(treatment: str) -> str:
    """Map a treatment label to its severity tier."""
    if not isinstance(treatment, str):
        return "Other"
    if "as recognized by" in treatment:
        return "Related"
    return SEVERITY_BY_TREATMENT.get(treatment, "Other")


def direction_for(treatment: str) -> str:
    """Coarse direction inference. Real pipeline assigns this directly;
    in the mock we infer from the treatment label."""
    if "as recognized by" in treatment:
        return "Related Reference"
    if treatment in {
        "Reversed by",
        "Reversed and remanded by",
        "Vacated by",
        "Vacated and remanded by",
        "Affirmed by",
        "Affirmed in part; Reversed in part by",
        "Affirmed in part; Vacated in part by",
        "Cert. denied by",
        "Cert. granted by",
        "Remanded by",
    }:
        return "Direct History"
    return "Citing Reference"


# ── Document body rendering ────────────────────────────────────────────
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
CITED_CASE_RE = re.compile(
    r'<citedCase data-cluster-id="(\d+)">(.+?)</citedCase>'
)


def excerpt_from_text(document_text: str, max_chars: int = 280) -> str:
    """First-paragraph plain-text excerpt for the search results card."""
    text = SECTION_RE.sub("", document_text)
    text = CITED_CASE_RE.sub(r"\2", text)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return ""
    first = paragraphs[0]
    if len(first) <= max_chars:
        return first
    truncated = first[:max_chars]
    cut = truncated.rfind(". ")
    if cut > max_chars * 0.6:
        return truncated[: cut + 1]
    return truncated.rstrip() + "…"


def section_anchor(section_id: str) -> str:
    """Turn a section ID like 'II.A' into a URL-safe anchor 'section-II-A'."""
    safe = re.sub(r"[^A-Za-z0-9]+", "-", section_id).strip("-")
    return f"section-{safe}"


def render_body_html(document_text: str) -> tuple[str, list[dict]]:
    """Render the mock document_text into HTML.

    - `## I` headings become <section id="section-I"><h2>I</h2>...</section>.
    - Blank-line-separated runs become <p>...</p>.
    - <citedCase data-cluster-id="N"> spans become either <a> (if scoped)
      or <span class="cited-case"> (if non-scoped).

    Returns (html, sections) where sections is the metadata list for
    the data contract.
    """
    text = document_text.strip()
    parts = SECTION_RE.split(text)
    # parts after split: [pre-text, sec1_id, sec1_body, sec2_id, sec2_body, ...]
    # If document doesn't start with a heading, parts[0] is leading content;
    # ignore for the section list (it's typically empty).
    pre = parts[0]
    section_pairs = list(zip(parts[1::2], parts[2::2], strict=False))

    sections_meta = [
        {
            "id": sid.strip(),
            "title": sid.strip(),
            "anchor": section_anchor(sid.strip()),
        }
        for sid, _ in section_pairs
    ]

    out_chunks: list[str] = []
    if pre.strip():
        out_chunks.append(_render_paragraphs(pre))
    for sid, body in section_pairs:
        sid_clean = sid.strip()
        anchor = section_anchor(sid_clean)
        out_chunks.append(
            f'<section id="{anchor}" data-section-id="{escape(sid_clean)}">'
            f"<h2>{escape(sid_clean)}</h2>"
            f"{_render_paragraphs(body)}"
            f"</section>"
        )
    return "\n".join(out_chunks), sections_meta


def _render_paragraphs(text: str) -> str:
    """Wrap blank-line-separated runs in <p>...</p> with citation markup
    transformed."""
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    rendered = []
    for p in paragraphs:
        # Escape everything that isn't a citedCase tag, then process tags.
        # Simpler approach: process citedCase first, then escape the rest
        # by chunks. Do a regex split.
        out = []
        last = 0
        for m in CITED_CASE_RE.finditer(p):
            out.append(escape(p[last : m.start()]))
            cluster_id = int(m.group(1))
            label = m.group(2)
            if cluster_id in SCOPED_CLUSTER_IDS:
                out.append(
                    f'<a class="cited-case cited-case--scoped" '
                    f'href="/opinion/{cluster_id}/">{escape(label)}</a>'
                )
            else:
                out.append(f'<span class="cited-case">{escape(label)}</span>')
            last = m.end()
        out.append(escape(p[last:]))
        rendered.append(f"<p>{''.join(out)}</p>")
    return "\n".join(rendered)


# ── Quote-in-context lookup ────────────────────────────────────────────
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def find_quote_context(
    document_text: str, quote: str, n_sentences: int = 3
) -> dict:
    """Locate `quote` inside the opinion body and return the N sentences
    before and after it. Used to render the supporting-quote highlight on
    the Authorities tab in document context."""
    plain = CITED_CASE_RE.sub(r"\2", document_text)
    plain = SECTION_RE.sub("", plain)
    plain = re.sub(r"\s+", " ", plain).strip()

    idx = plain.lower().find(quote.lower())
    if idx < 0:
        return {"before": "", "quote": quote, "after": ""}

    quote_actual = plain[idx : idx + len(quote)]
    before_text = plain[:idx].strip()
    after_text = plain[idx + len(quote) :].strip()

    before_sentences = [s for s in SENTENCE_SPLIT_RE.split(before_text) if s]
    after_sentences = [s for s in SENTENCE_SPLIT_RE.split(after_text) if s]

    return {
        "before": " ".join(before_sentences[-n_sentences:]),
        "quote": quote_actual,
        "after": " ".join(after_sentences[:n_sentences]),
    }


# ── Active-voice rewriting (for the Authorities tab) ───────────────────
# The canonical treatments are passive ("Overruled by"). Authorities views
# show what *this* opinion did to its cited cases, so the verb flips to
# active voice ("Overrules"). Cited By keeps the passive form unchanged.
ACTIVE_VOICE = {
    "Reversed by": "Reverses",
    "Reversed and remanded by": "Reverses and remands",
    "Vacated by": "Vacates",
    "Vacated and remanded by": "Vacates and remands",
    "Overruled by": "Overrules",
    "Abrogated by": "Abrogates",
    "Questioned by": "Questions",
    "Affirmed in part; Reversed in part by": "Affirms in part; Reverses in part",
    "Affirmed in part; Vacated in part by": "Affirms in part; Vacates in part",
    "Disapproved by": "Disapproves",
    "Limited by": "Limits",
    "Remanded by": "Remands",
    "Cert. granted by": "Granted cert.",
    "Criticized by": "Criticizes",
    "Distinguished by": "Distinguishes",
    "Declined to follow by": "Declines to follow",
    "Dismissed by": "Dismisses",
    "Affirmed by": "Affirms",
    "Cert. denied by": "Denied cert.",
    "Cited by": "Cites",
}


def to_active_voice(treatment: str) -> str:
    if treatment in ACTIVE_VOICE:
        return ACTIVE_VOICE[treatment]
    # "Overruled as recognized by" → "Overruled as recognized"
    if treatment.endswith(" by"):
        return treatment[:-3]
    return treatment


# ── Authority + Cited By transformation ────────────────────────────────
def transform_authority(row: dict, idx: int, document_text: str) -> dict:
    treatment = row["treatment"]
    severity = severity_for(treatment)
    return {
        "row_id": f"auth-{idx}",
        "cited_cluster_id": row["cited_cluster_id"],
        "cited_case_name": row["cited_case_name"],
        "cited_citation": row["cited_citation"],
        "is_scoped": row["cited_cluster_id"] in SCOPED_CLUSTER_IDS,
        "treatment": treatment,
        "treatment_active": to_active_voice(treatment),
        "severity": severity,
        "direction": direction_for(treatment),
        "section_id": row["section_id"],
        "section_anchor": section_anchor(row["section_id"])
        if row["section_id"]
        else "",
        "validation": {
            "state": row["validation_state"],
            "expert_treatment": row["expert_treatment"],
        },
        "expand": {
            "quote": row["quote"],
            "rationale": row["rationale"],
            "context": find_quote_context(document_text, row["quote"]),
        },
    }


def cb_context(row: dict, cited_case_name: str) -> dict:
    """Build the supporting-quote context for a cited_by row.

    If the row provides a real `body_excerpt` containing the quote, slice
    context out of it via `find_quote_context`. Otherwise synthesize a short
    generic frame so every row shows the quote in *some* surrounding text.

    The synthesized version is mock-only; the real-data swap (#13) will
    supply each citing opinion's body and produce real context.
    """
    quote = row["quote"]
    excerpt = row.get("body_excerpt")
    if excerpt and quote.lower() in excerpt.lower():
        return find_quote_context(excerpt, quote)
    return {
        "before": (
            "After reviewing the briefing and the relevant authorities, "
            "the court reasoned that"
        ),
        "quote": quote,
        "after": "and on that basis resolved the question before it.",
    }


def transform_cited_by(
    row: dict, idx: int, cited_case_name: str
) -> dict:
    treatment = row["treatment"]
    severity = severity_for(treatment)
    return {
        "row_id": f"cb-{idx}",
        "citing_cluster_id": row["citing_cluster_id"],
        "citing_case_name": row["citing_case_name"],
        "citing_citation": row["citing_citation"],
        "citing_court": row["citing_court"],
        "citing_court_display": COURT_DISPLAY.get(
            row["citing_court"], row["citing_court"]
        ),
        "citing_date_filed": row["citing_date_filed"],
        "is_scoped": row["citing_cluster_id"] in SCOPED_CLUSTER_IDS,
        "treatment": treatment,
        "severity": severity,
        "direction": direction_for(treatment),
        "validation": {
            "state": row["validation_state"],
            "expert_treatment": row["expert_treatment"],
        },
        "expand": {
            "quote": row["quote"],
            "rationale": row["rationale"],
            "context": cb_context(row, cited_case_name),
        },
    }


def sort_by_severity_then_date(
    rows: list[dict], date_key: str | None
) -> list[dict]:
    """Sort by severity tier (Stop first), then by date (newest first) if available."""

    def key(r: dict):
        sev_rank = SEVERITY_RANK.get(r["severity"], 99)
        if date_key and r.get(date_key):
            # negative ISO date for descending sort
            return (sev_rank, r[date_key])
        return (sev_rank, "")

    # For descending date within tier, sort once with negative key —
    # easier: sort by sev ascending, then by date descending in a stable second pass.
    rows = sorted(
        rows,
        key=lambda r: r.get(date_key, "") if date_key else "",
        reverse=True,
    )
    rows = sorted(rows, key=lambda r: SEVERITY_RANK.get(r["severity"], 99))
    return rows


def build_summary(cited_by_sorted: list[dict]) -> dict:
    """Compute most-negative + most-recent-negative + tier counts from cited_by."""
    counts = {
        tier.lower(): 0
        for tier in ("Stop", "Warning", "Caution", "Neutral", "Related")
    }
    for cb in cited_by_sorted:
        tier_key = cb["severity"].lower()
        if tier_key in counts:
            counts[tier_key] += 1

    # Most-negative: first row (since we already sorted by severity asc, date desc)
    # but only if its tier is in the negative set; otherwise no most-negative exists.
    most_negative = None
    for cb in cited_by_sorted:
        if cb["severity"] in NEGATIVE_TIERS:
            most_negative = _summary_pointer(cb)
            break

    # Most-recent-negative: of all negative-tier rows, the latest by date
    negative_rows = [
        cb for cb in cited_by_sorted if cb["severity"] in NEGATIVE_TIERS
    ]
    most_recent = None
    if negative_rows:
        latest = max(negative_rows, key=lambda r: r["citing_date_filed"])
        most_recent = _summary_pointer(latest)

    headline = most_negative
    if headline is None and cited_by_sorted:
        latest = max(cited_by_sorted, key=lambda r: r["citing_date_filed"])
        headline = _summary_pointer(latest)

    return {
        "most_negative": most_negative,
        "most_recent_negative": most_recent,
        "headline": headline,
        "counts": counts,
    }


def _summary_pointer(cb_row: dict) -> dict:
    """Compact version of a cited_by row for the summary header."""
    return {
        "treatment": cb_row["treatment"],
        "severity": cb_row["severity"],
        "citing_cluster_id": cb_row["citing_cluster_id"],
        "citing_case_name": cb_row["citing_case_name"],
        "citing_citation": cb_row["citing_citation"],
        "citing_court": cb_row["citing_court"],
        "citing_court_display": cb_row["citing_court_display"],
        "citing_date_filed": cb_row["citing_date_filed"],
        "is_scoped": cb_row["is_scoped"],
        "validation": cb_row["validation"],
        "expand": cb_row["expand"],
    }


# ── Main build ─────────────────────────────────────────────────────────
def build_opinion(opinion: dict) -> dict:
    body_html, sections = render_body_html(opinion["document_text"])

    authorities = [
        transform_authority(row, i, opinion["document_text"])
        for i, row in enumerate(opinion["authorities"])
    ]
    authorities = sort_by_severity_then_date(authorities, date_key=None)

    cited_by = [
        transform_cited_by(row, i, opinion["case_name"])
        for i, row in enumerate(opinion["cited_by"])
    ]
    cited_by = sort_by_severity_then_date(
        cited_by, date_key="citing_date_filed"
    )
    # Rank each row by citing_date_filed desc so the Cited By tab's
    # "Recency" sort can reorder via CSS `order:` without re-sorting in JS.
    by_date_desc = sorted(
        cited_by, key=lambda r: r["citing_date_filed"], reverse=True
    )
    for rank, row in enumerate(by_date_desc):
        row["recency_index"] = rank

    summary = build_summary(cited_by)

    return {
        "cluster_id": opinion["cluster_id"],
        "case_name": opinion["case_name"],
        "citations": opinion["citations"],
        "court": opinion["court"],
        "court_display": COURT_DISPLAY.get(opinion["court"], opinion["court"]),
        "date_filed": opinion["date_filed"],
        "excerpt": excerpt_from_text(opinion["document_text"]),
        "summary": summary,
        "document": {
            "body_html": body_html,
            "sections": sections,
        },
        "authorities": authorities,
        "cited_by": cited_by,
    }


def build_index_entry(opinion_data: dict) -> dict:
    """Subset of opinion data for the global Search Results listing."""
    return {
        "cluster_id": opinion_data["cluster_id"],
        "case_name": opinion_data["case_name"],
        "citations": opinion_data["citations"],
        "court": opinion_data["court"],
        "court_display": opinion_data["court_display"],
        "date_filed": opinion_data["date_filed"],
        "excerpt": opinion_data["excerpt"],
        "summary": opinion_data["summary"],
    }


def main() -> None:
    OPINIONS_OUT.mkdir(parents=True, exist_ok=True)

    index_entries: list[dict] = []
    for opinion in MOCK_OPINIONS:
        data = build_opinion(opinion)
        out_path = OPINIONS_OUT / f"{data['cluster_id']}.json"
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        index_entries.append(build_index_entry(data))

    # Sort index alphabetically by case name (default sort per design doc)
    index_entries.sort(key=lambda e: e["case_name"].lower())

    index_path = OUT_DIR / "index.json"
    index_path.write_text(
        json.dumps(index_entries, indent=2, ensure_ascii=False)
    )

    print(f"Wrote {len(MOCK_OPINIONS)} opinion JSONs to {OPINIONS_OUT}")
    print(
        f"Wrote index.json with {len(index_entries)} entries to {index_path}"
    )


if __name__ == "__main__":
    main()
