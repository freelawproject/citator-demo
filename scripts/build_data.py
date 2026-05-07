"""Transforms mock fixtures (or, eventually, real inference output) into the
Eleventy data contract documented in
ai-research/citator_launch_plan/demo_site_design.md § Data contract.

Outputs:
    _data/opinions/{cluster_id}.json   one per scoped opinion
    _data/index.json                    global listing for Search Results

Real-data swap (issue #13) replaces the mock_data import below with a function
that reads CSVs from data-source/.

Single-source-of-truth: mock_data.EDGES is the canonical list of treatment
relationships. authorities[] (where opinion = citing side) and cited_by[]
(where opinion = cited side) are derived views — no double-authoring, no
drift, mirroring production's CitatorTreatment table.
"""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

from mock_data import (
    CATEGORY_DISPLAY,
    CATEGORY_JURISDICTION,
    CATEGORY_ORDER,
    COURT_CATEGORY,
    COURT_DISPLAY,
    COURT_LEVEL,
    COURTS_OF_LAST_RESORT,
    EDGES,
    EXTERNAL_OPINIONS,
    JURISDICTION_DISPLAY,
    JURISDICTION_ORDER,
    SCOPED_CLUSTER_IDS,
    SCOPED_OPINIONS,
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
    "Neutral": 3,
}
NEGATIVE_TIERS = {"Stop", "Warning", "Caution"}

# Treatments that produce Direct History direction (procedural appellate
# review of the same case).
DIRECT_HISTORY_TREATMENTS = {
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
    "Dismissed by",
}

# Treatments that require the citing court to have authority over the cited
# court (vertical_binding) or be the same court (self). Sister-court
# applications are not legally possible for these.
VERTICAL_OR_SELF_TREATMENTS = DIRECT_HISTORY_TREATMENTS | {
    "Overruled by",
    "Abrogated by",
}

OUT_DIR = Path(__file__).parent.parent / "_data"
OPINIONS_OUT = OUT_DIR / "opinions"


def severity_for(treatment: str) -> str:
    """Map a treatment label to its severity tier.

    "As recognized by" treatments inherit the underlying treatment's tier
    per the canonical taxonomy in `ai-research/CLAUDE.md` § Treatments —
    e.g., "Overruled as recognized by" → Stop (because Overruled by is
    Stop), "Limited as recognized by" → Warning. The "Related" pseudo-
    tier from earlier mock revisions is gone; Related Reference is a
    direction (in `direction_for`), not a severity.
    """
    if not isinstance(treatment, str):
        return "Other"
    if "as recognized by" in treatment:
        treatment = treatment.replace(" as recognized", "")
    return SEVERITY_BY_TREATMENT.get(treatment, "Other")


def direction_for(treatment: str) -> str:
    if "as recognized by" in treatment:
        return "Related Reference"
    if treatment in DIRECT_HISTORY_TREATMENTS:
        return "Direct History"
    return "Citing Reference"


# ── Document body rendering ────────────────────────────────────────────
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
CITED_CASE_RE = re.compile(
    r'<citedCase data-cluster-id="(\d+)">(.+?)</citedCase>'
)


def excerpt_from_text(document_text: str, max_chars: int = 280) -> str:
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
    safe = re.sub(r"[^A-Za-z0-9]+", "-", section_id).strip("-")
    return f"section-{safe}" if safe else ""


def render_body_html(document_text: str) -> tuple[str, list[dict]]:
    text = document_text.strip()
    parts = SECTION_RE.split(text)
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
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    rendered = []
    for p in paragraphs:
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
    section_context: str, quote: str, n_sentences: int = 3
) -> dict:
    """Slice up to N sentences before/after the quote inside the citing
    opinion's section_context paragraph. Returns {before, quote, after}."""
    if not section_context:
        return {"before": "", "quote": quote, "after": ""}
    plain = re.sub(r"\s+", " ", section_context).strip()
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


# ── Active-voice rewriting (Authorities tab) ───────────────────────────
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
    # "X as recognized by" → "Recognizes as x" (the citing opinion notes
    # that the cited authority was previously X'd by some other case).
    if "as recognized by" in treatment:
        base = treatment.replace(" as recognized by", "").strip()
        return f"Recognizes as {base.lower()}"
    if treatment.endswith(" by"):
        return treatment[:-3]
    return treatment


# ── Opinion lookup ─────────────────────────────────────────────────────
def _build_opinion_index() -> dict[int, dict]:
    """Combined lookup of all opinion metadata (scoped + external),
    keyed by cluster_id."""
    idx: dict[int, dict] = {}
    for op in SCOPED_OPINIONS:
        idx[op["cluster_id"]] = op
    for cid, ext in EXTERNAL_OPINIONS.items():
        idx[cid] = ext
    return idx


OPINION_INDEX = _build_opinion_index()


def _enrich_court(record: dict) -> dict:
    return {
        **record,
        "court_display": COURT_DISPLAY.get(record["court"], record["court"]),
        "court_level": COURT_LEVEL.get(record["court"]),
    }


# ── Hierarchy validation ───────────────────────────────────────────────
class HierarchyError(ValueError):
    pass


def validate_edge(edge: dict) -> None:
    """Raise if the edge's (treatment, citing_level, cited_level) tuple is
    hierarchically impossible. Citation references are permissive; direct
    history and overrule-class treatments require vertical or self."""
    treatment = edge["treatment"]
    citing_id = edge["citing_cluster_id"]
    cited_id = edge["cited_cluster_id"]
    citing_op = OPINION_INDEX.get(citing_id)
    cited_op = OPINION_INDEX.get(cited_id)
    if citing_op is None or cited_op is None:
        raise HierarchyError(
            f"Edge references unknown cluster: {citing_id} -> {cited_id}"
        )
    citing_level = COURT_LEVEL.get(citing_op["court"])
    cited_level = COURT_LEVEL.get(cited_op["court"])
    if citing_level is None or cited_level is None:
        raise HierarchyError(
            f"Edge references court without level: "
            f"{citing_op['court']} -> {cited_op['court']}"
        )

    # Temporal: citing case must be filed after cited case
    if (
        edge["citing_cluster_id"] != edge["cited_cluster_id"]
        and citing_op["date_filed"] <= cited_op["date_filed"]
    ):
        raise HierarchyError(
            f"Temporal violation: {citing_op['case_name']} "
            f"({citing_op['date_filed']}) cannot cite "
            f"{cited_op['case_name']} ({cited_op['date_filed']})"
        )

    # Direct-history treatments require citing strictly higher than cited.
    if treatment in DIRECT_HISTORY_TREATMENTS and citing_level >= cited_level:
        raise HierarchyError(
            f"Direct-history treatment '{treatment}' requires citing "
            f"court above cited court: "
            f"{citing_op['case_name']} ({citing_op['court']}) -> "
            f"{cited_op['case_name']} ({cited_op['court']})"
        )
    # Other vertical-or-self treatments (Overruled by, Abrogated by) require
    # citing court at or above cited court.
    elif (
        treatment in VERTICAL_OR_SELF_TREATMENTS and citing_level > cited_level
    ):
        raise HierarchyError(
            f"Treatment '{treatment}' requires citing court at or above "
            f"cited court: "
            f"{citing_op['case_name']} ({citing_op['court']}) -> "
            f"{cited_op['case_name']} ({cited_op['court']})"
        )


# ── Edge → view conversion ─────────────────────────────────────────────
def _row_id(prefix: str, edge_idx: int) -> str:
    return f"{prefix}-{edge_idx}"


def edge_to_authority_view(edge: dict, edge_idx: int) -> dict:
    """For the citing side: this opinion's `authorities[]` entry."""
    cited = _enrich_court(OPINION_INDEX[edge["cited_cluster_id"]])
    treatment = edge["treatment"]
    return {
        "row_id": _row_id("auth", edge_idx),
        "cited_cluster_id": cited["cluster_id"],
        "cited_case_name": cited["case_name"],
        "cited_docket_number": cited.get("docket_number", ""),
        "cited_citations": cited["citations"],
        "cited_court": cited["court"],
        "cited_court_display": cited["court_display"],
        "cited_date_filed": cited["date_filed"],
        "is_scoped": cited["cluster_id"] in SCOPED_CLUSTER_IDS,
        "treatment": treatment,
        "treatment_active": to_active_voice(treatment),
        "severity": severity_for(treatment),
        "direction": direction_for(treatment),
        "source": edge["source"],
        "expert_treatment": edge["expert_treatment"],
        "expand": {
            "quote": edge["quote"],
            "rationale": edge["rationale"],
            "context": find_quote_context(
                edge["section_context"], edge["quote"]
            ),
        },
    }


def edge_to_cited_by_view(edge: dict, edge_idx: int) -> dict:
    """For the cited side: this opinion's `cited_by[]` entry."""
    citing = _enrich_court(OPINION_INDEX[edge["citing_cluster_id"]])
    treatment = edge["treatment"]
    return {
        "row_id": _row_id("cb", edge_idx),
        "citing_cluster_id": citing["cluster_id"],
        "citing_case_name": citing["case_name"],
        "citing_docket_number": citing.get("docket_number", ""),
        "citing_citations": citing["citations"],
        "citing_court": citing["court"],
        "citing_court_display": citing["court_display"],
        "citing_date_filed": citing["date_filed"],
        "is_scoped": citing["cluster_id"] in SCOPED_CLUSTER_IDS,
        "treatment": treatment,
        "severity": severity_for(treatment),
        "direction": direction_for(treatment),
        "source": edge["source"],
        "expert_treatment": edge["expert_treatment"],
        "expand": {
            "quote": edge["quote"],
            "rationale": edge["rationale"],
            "context": find_quote_context(
                edge["section_context"], edge["quote"]
            ),
        },
    }


def sort_authorities(rows: list[dict]) -> list[dict]:
    """Severity asc within tier; cited cases without dates fall to end."""
    rows = sorted(
        rows, key=lambda r: r.get("cited_date_filed", ""), reverse=True
    )
    rows = sorted(rows, key=lambda r: SEVERITY_RANK.get(r["severity"], 99))
    return rows


def sort_cited_by(rows: list[dict]) -> list[dict]:
    """Severity asc, then date desc within tier. Adds recency_index for
    the Cited By tab's secondary "Recency" sort."""
    rows = sorted(rows, key=lambda r: r["citing_date_filed"], reverse=True)
    rows = sorted(rows, key=lambda r: SEVERITY_RANK.get(r["severity"], 99))
    by_date_desc = sorted(
        rows, key=lambda r: r["citing_date_filed"], reverse=True
    )
    for rank, row in enumerate(by_date_desc):
        row["recency_index"] = rank
    return rows


# ── Per-cluster edge expansion ─────────────────────────────────────────
def collect_edges_per_cluster() -> tuple[
    dict[int, list[dict]], dict[int, list[dict]]
]:
    """Walk EDGES once. Return (authorities_by_cluster, cited_by_by_cluster).

    Authorities map: cluster_id -> list of edge views where cluster is the
    citing side. Cited_by map: cluster_id -> list of edge views where
    cluster is the cited side.
    """
    authorities: dict[int, list[dict]] = {}
    cited_by: dict[int, list[dict]] = {}

    for idx, edge in enumerate(EDGES):
        validate_edge(edge)

        citing_id = edge["citing_cluster_id"]
        cited_id = edge["cited_cluster_id"]

        # Authorities view — only emitted when citing side is scoped
        if citing_id in SCOPED_CLUSTER_IDS:
            authorities.setdefault(citing_id, []).append(
                edge_to_authority_view(edge, idx)
            )

        # Cited_by view — only emitted when cited side is scoped
        if cited_id in SCOPED_CLUSTER_IDS:
            cited_by.setdefault(cited_id, []).append(
                edge_to_cited_by_view(edge, idx)
            )

    return authorities, cited_by


# ── Summary computation (FK-pointer style) ─────────────────────────────
def _summary_pointer_from_view(view_row: dict) -> dict:
    """Compact pointer derived from a cited_by view row — used by the
    opinion-page summary cards. Intentionally subset of the full view row;
    matches what `treatmentBlock` / `treatmentLine` consume."""
    return {
        "row_id": view_row["row_id"],
        "treatment": view_row["treatment"],
        "severity": view_row["severity"],
        "direction": view_row["direction"],
        "citing_cluster_id": view_row["citing_cluster_id"],
        "citing_case_name": view_row["citing_case_name"],
        "citing_docket_number": view_row.get("citing_docket_number", ""),
        "citing_citations": view_row["citing_citations"],
        "citing_court": view_row["citing_court"],
        "citing_court_display": view_row["citing_court_display"],
        "citing_date_filed": view_row["citing_date_filed"],
        "is_scoped": view_row["is_scoped"],
        "source": view_row["source"],
        "expert_treatment": view_row["expert_treatment"],
        "expand": view_row["expand"],
    }


def build_summary(cited_by_sorted: list[dict]) -> dict:
    """Compute the two FK pointers per the production CitatorClusterSummary
    spec (FK-only flavor — no denormalized counts/dates; see db_design.md
    § Cluster summaries)."""
    citing_negative = [
        cb
        for cb in cited_by_sorted
        if cb["direction"] != "Direct History"
        and cb["severity"] in NEGATIVE_TIERS
    ]
    most_severe = (
        _summary_pointer_from_view(citing_negative[0])
        if citing_negative
        else None
    )

    direct = [
        cb for cb in cited_by_sorted if cb["direction"] == "Direct History"
    ]
    direct_history = _summary_pointer_from_view(direct[0]) if direct else None

    # Headline for search-results card: prefer most-severe negative; else
    # direct-history (any tier); else latest cited_by entry.
    headline = most_severe
    if headline is None and direct_history is not None:
        headline = direct_history
    if headline is None and cited_by_sorted:
        latest_any = max(cited_by_sorted, key=lambda r: r["citing_date_filed"])
        headline = _summary_pointer_from_view(latest_any)

    # `cr_severity` is the most-severe NON-direct-history cited_by tier
    # (any tier including Neutral). Used by the search-results filter
    # rail's tabbed severity filter — distinct from `most_severe_treatment`,
    # which is restricted to negative tiers and drives the opinion-page
    # summary picker.
    citing_any = [
        cb for cb in cited_by_sorted if cb["direction"] != "Direct History"
    ]
    cr_severity = citing_any[0]["severity"] if citing_any else None

    dh_severity = direct[0]["severity"] if direct else None

    return {
        "most_severe_treatment": most_severe,
        "direct_history": direct_history,
        "headline": headline,
        "dh_severity": dh_severity,
        "cr_severity": cr_severity,
    }


# ── Main build ─────────────────────────────────────────────────────────
def build_opinion(
    opinion: dict,
    authorities_for_cluster: list[dict],
    cited_by_for_cluster: list[dict],
) -> dict:
    body_html, sections = render_body_html(opinion["document_text"])
    authorities = sort_authorities(list(authorities_for_cluster))
    cited_by = sort_cited_by(list(cited_by_for_cluster))
    summary = build_summary(cited_by)
    enriched = _enrich_court(opinion)
    return {
        "cluster_id": enriched["cluster_id"],
        "case_name": enriched["case_name"],
        "docket_number": enriched["docket_number"],
        "citations": enriched["citations"],
        "court": enriched["court"],
        "court_display": enriched["court_display"],
        "is_court_of_last_resort": opinion["court"] in COURTS_OF_LAST_RESORT,
        "date_filed": enriched["date_filed"],
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
    return {
        "cluster_id": opinion_data["cluster_id"],
        "case_name": opinion_data["case_name"],
        "docket_number": opinion_data["docket_number"],
        "citations": opinion_data["citations"],
        "court": opinion_data["court"],
        "court_display": opinion_data["court_display"],
        "is_court_of_last_resort": opinion_data["is_court_of_last_resort"],
        "date_filed": opinion_data["date_filed"],
        "excerpt": opinion_data["excerpt"],
        "summary": opinion_data["summary"],
    }


def main() -> None:
    OPINIONS_OUT.mkdir(parents=True, exist_ok=True)
    authorities_by_cluster, cited_by_by_cluster = collect_edges_per_cluster()

    index_entries: list[dict] = []
    for op in SCOPED_OPINIONS:
        cid = op["cluster_id"]
        data = build_opinion(
            op,
            authorities_by_cluster.get(cid, []),
            cited_by_by_cluster.get(cid, []),
        )
        out_path = OPINIONS_OUT / f"{cid}.json"
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        index_entries.append(build_index_entry(data))

    index_entries.sort(key=lambda e: e["case_name"].lower())
    index_path = OUT_DIR / "index.json"
    index_path.write_text(
        json.dumps(index_entries, indent=2, ensure_ascii=False)
    )

    # Emit a courts list for the search-results filter rail. Sorted by
    # hierarchy (level 0 first), then alphabetical by display name within
    # a level. Each entry includes a `category` for the parent-checkbox
    # group on the filter rail. The filter rail uses this as the single
    # source of truth for court labels — no more inline courtNames dict
    # in index.njk.
    courts_list = sorted(
        (
            {
                "key": key,
                "display": COURT_DISPLAY.get(key, key),
                "level": COURT_LEVEL.get(key, 99),
                "category": COURT_CATEGORY.get(key, "other"),
            }
            for key in COURT_DISPLAY
        ),
        key=lambda c: (c["level"], c["display"].lower()),
    )
    courts_path = OUT_DIR / "courts.json"
    courts_path.write_text(
        json.dumps(courts_list, indent=2, ensure_ascii=False)
    )

    # Court categories — each entry has a stable key + display name +
    # jurisdiction + an order index that drives the filter rail's group
    # order.
    categories_list = [
        {
            "key": cat,
            "display": CATEGORY_DISPLAY[cat],
            "jurisdiction": CATEGORY_JURISDICTION.get(cat),
            "order": idx,
        }
        for idx, cat in enumerate(CATEGORY_ORDER)
        if cat in CATEGORY_DISPLAY
    ]
    categories_path = OUT_DIR / "court_categories.json"
    categories_path.write_text(
        json.dumps(categories_list, indent=2, ensure_ascii=False)
    )

    # Jurisdictions list — drives the top-level parent checkbox in the
    # filter rail (Federal / State).
    jurisdictions_list = [
        {
            "key": jur,
            "display": JURISDICTION_DISPLAY[jur],
            "order": idx,
        }
        for idx, jur in enumerate(JURISDICTION_ORDER)
        if jur in JURISDICTION_DISPLAY
    ]
    jurisdictions_path = OUT_DIR / "court_jurisdictions.json"
    jurisdictions_path.write_text(
        json.dumps(jurisdictions_list, indent=2, ensure_ascii=False)
    )

    print(f"Wrote {len(SCOPED_OPINIONS)} opinion JSONs to {OPINIONS_OUT}")
    print(
        f"Wrote index.json with {len(index_entries)} entries to {index_path}"
    )
    print(f"Wrote courts.json with {len(courts_list)} entries")
    print(f"Wrote court_categories.json with {len(categories_list)} entries")
    print(
        f"Wrote court_jurisdictions.json with {len(jurisdictions_list)} entries"
    )
    print(f"Validated {len(EDGES)} edges (hierarchy + temporal)")


if __name__ == "__main__":
    main()
