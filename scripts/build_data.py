"""Build the JSON the Eleventy templates consume.

Reads a data module (`real_data` by default, `mock_data` when
CITATOR_DEMO_DATA=mock) and writes to `_data/`:

    opinions/{cluster_id}.json  one per opinion page
    index.json                  the home page's opinion list
    scope.json                  counts for the About page
    flags.json                  build flags (see FLAGS)
    courts.json                 every court in scope
    court_picker.json           the home page's court picker
    court_categories.json, court_jurisdictions.json
    treatments.json             the treatment taxonomy by severity tier
    treatment_definitions.json  every pill label → its definition

The data source's `edges` are the single record of treatments. The Cited
By tab of a cited opinion is derived from them; the Authorities tab of a
citing opinion comes from its `citation_groups` rows.

Environment:
    CITATOR_DEMO_DATA=mock         build from the hand-written fixtures
    CITATOR_DEMO_VALIDATION=1      show the expert-validation marks
"""

from __future__ import annotations

import importlib
import json
import os
import re
from pathlib import Path
from typing import Any

from courts import court_list, court_picker_tabs
from data_source import DataSource, JsonDict, short_date
from history import AppellateHistory
from model_output import (
    disposition_label,
    document_token_streams,
    expand_quote,
    quote_names_case,
    verify_quote,
)
from render import excerpt_from_text, render_body_html
from taxonomy import (
    DIRECT_HISTORY_TREATMENTS,
    NEGATIVE_TIERS,
    VERTICAL_OR_SELF_TREATMENTS,
    base_treatment,
    definition_lookup,
    direction_for,
    has_evidence,
    is_recognized,
    past_tense,
    recognized_form,
    recognizes_label,
    row_validation,
    severity_for,
    severity_rank,
    to_active_voice,
    treatment_table,
    validate_pills,
    worst_tier,
)

OUT_DIR = Path(__file__).parent.parent / "_data"
OPINIONS_OUT = OUT_DIR / "opinions"
CL_OPINION_URL = "https://www.courtlistener.com/opinion/{cluster_id}/x/"

# Build flags, written to _data/flags.json and read by the templates.
# `validation`: show the marks comparing each treatment with the expert's
# label. An internal review aid, off unless the build asks for it.
FLAGS: dict[str, bool] = {
    "validation": os.environ.get("CITATOR_DEMO_VALIDATION", "")
    not in ("", "0", "false"),
}


def load_data_source() -> DataSource:
    """The data module named by CITATOR_DEMO_DATA (default: real data)."""
    name = (
        "mock_data"
        if os.environ.get("CITATOR_DEMO_DATA") == "mock"
        else "real_data"
    )
    module = importlib.import_module(name)
    source: DataSource = module.load()
    return source


# ── Edge validation ─────────────────────────────────────────────────────
class HierarchyError(ValueError):
    """An edge the court hierarchy or the dates rule out. `kind` is
    "temporal" (the citing opinion predates the cited one, so the link is
    wrong) or "hierarchy" (the treatment needs a higher court)."""

    def __init__(self, message: str, kind: str = "hierarchy") -> None:
        super().__init__(message)
        self.kind = kind


def validate_edge(
    edge: JsonDict, index: dict[int, JsonDict], court_level: dict[str, int]
) -> None:
    """Raise HierarchyError when an edge is impossible. Citing references
    are permissive; direct history needs a strictly higher citing court,
    overruling-class treatments a court at or above the cited one."""
    treatment = edge["treatment"]
    citing = index.get(edge["citing_cluster_id"])
    cited = index.get(edge["cited_cluster_id"])
    if citing is None or cited is None:
        raise HierarchyError(
            f"Edge references unknown cluster: "
            f"{edge['citing_cluster_id']} -> {edge['cited_cluster_id']}"
        )
    citing_level = court_level.get(citing["court"])
    cited_level = court_level.get(cited["court"])
    if citing_level is None or cited_level is None:
        raise HierarchyError(
            f"Edge references court without level: "
            f"{citing['court']} -> {cited['court']}"
        )
    pair = (
        f"{citing['case_name']} ({citing['court']}) -> "
        f"{cited['case_name']} ({cited['court']})"
    )
    if (
        edge["citing_cluster_id"] != edge["cited_cluster_id"]
        and citing["date_filed"] <= cited["date_filed"]
    ):
        raise HierarchyError(
            f"Temporal violation: {citing['case_name']} "
            f"({citing['date_filed']}) cannot cite "
            f"{cited['case_name']} ({cited['date_filed']})",
            kind="temporal",
        )
    if treatment in DIRECT_HISTORY_TREATMENTS and citing_level >= cited_level:
        raise HierarchyError(
            f"Direct-history treatment '{treatment}' requires citing court "
            f"above cited court: {pair}"
        )
    if treatment in VERTICAL_OR_SELF_TREATMENTS and citing_level > cited_level:
        raise HierarchyError(
            f"Treatment '{treatment}' requires citing court at or above "
            f"cited court: {pair}"
        )


# ── Sort keys ───────────────────────────────────────────────────────────
def _name_key(name: str) -> tuple[bool, str]:
    """Alphabetical key ignoring case and punctuation; unnamed opinions
    sort last."""
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower()).strip()
    return (not cleaned or cleaned.startswith("unnamed opinion"), cleaned)


def _desc(value: str) -> tuple[bool, tuple[int, ...]]:
    """Key that sorts ISO dates newest first and undated values last."""
    return (not value, tuple(-ord(c) for c in value))


def _stamp_ranks(rows: list[JsonDict], keys: dict[str, Any]) -> None:
    """Write each row's position under every sort key, so the tab can
    reorder with CSS `order` instead of rebuilding the list."""
    for field, key in keys.items():
        for rank, row in enumerate(sorted(rows, key=key)):
            row[field] = rank


# ── Cited By rows ───────────────────────────────────────────────────────
def _pill(kind: str, row: JsonDict) -> JsonDict:
    """One treatment on a Cited By row: what the citing opinion did
    (applied) or reports another court did (recognized)."""
    return {
        "kind": kind,
        "acting_case": row.get("acting_case") or "",
        "treatment": row["treatment"],
        "treatment_past": past_tense(row["treatment"]),
        "severity": row["severity"],
        "direction": row["direction"],
        "expert_treatment": row.get("expert_treatment"),
        "source": row.get("source", "model"),
        "evidence": row.get("evidence") or {},
    }


def _evidence_card(pill: JsonDict, label: str) -> JsonDict:
    evidence = pill["evidence"]
    return {
        "treatment": pill["treatment"],
        "label": label,
        "severity": pill["severity"],
        "rationale": evidence.get("rationale", ""),
        "quote": evidence.get("quote", ""),
        "quote_status": evidence.get("quote_status", ""),
        "quote_names": evidence.get("quote_names", ""),
    }


def select_evidence_cards(cards: list[JsonDict]) -> list[JsonDict]:
    """The cards a row presents: one per treatment other than a plain
    citation (taxonomy.has_evidence). Both tabs use this."""
    return [c for c in cards if has_evidence(c["treatment"])]


def has_detail(cards: list[JsonDict]) -> bool:
    """Whether a row expands: it has a card with something to show."""
    return any(c["quote"] or c["rationale"] for c in cards)


def group_cited_by(rows: list[JsonDict]) -> list[JsonDict]:
    """One row per citing opinion, however many treatments it applied.

    The row carries the treatment the citing opinion applied itself, the
    ones it recognizes other courts applied, one evidence card per
    treatment other than a plain citation, and the worst severity of them
    all, which is what the severity filter and the sort see.
    """
    grouped: dict[int, JsonDict] = {}
    for row in rows:
        cid = row["citing_cluster_id"]
        head = grouped.get(cid)
        if head is None:
            head = grouped[cid] = {**row, "applied": [], "recognized": []}
        kind = "recognized" if is_recognized(row["treatment"]) else "applied"
        head[kind].append(_pill(kind, row))
    out = []
    for head in grouped.values():
        by_severity = lambda p: severity_rank(p["severity"])  # noqa: E731
        head["applied"].sort(key=by_severity)
        head["recognized"].sort(key=by_severity)
        pills = sorted(head["applied"] + head["recognized"], key=by_severity)
        # the row speaks with the citing opinion's own worst treatment; a
        # row that only reports other courts' treatments speaks with those
        lead = (head["applied"] or head["recognized"])[0]
        head["treatment"] = lead["treatment"]
        head["direction"] = lead["direction"]
        head["expert_treatment"] = lead.get("expert_treatment")
        head["severity"] = worst_tier(p["severity"] for p in pills)
        states = validate_pills(
            [
                {
                    "kind": p["kind"],
                    "treatment": base_treatment(p["treatment"]),
                    "severity": p["severity"],
                }
                for p in pills
            ],
            head["expert_treatment"] or "",
        )
        for p, state in zip(pills, states, strict=True):
            p["validation"] = state
        head["validation"] = row_validation(states)
        head["recognized_filter"] = worst_tier(
            (p["severity"] for p in head["recognized"]), default="none"
        )
        # one card per pill, in the row's order: what the citing opinion
        # did, then what it recognizes, each by severity. The card pill
        # repeats the row pill word for word: on this tab a treatment
        # reads from the cited case's side
        cards = [
            _evidence_card(p, p["treatment"])
            for p in head["applied"] + head["recognized"]
        ]
        head["evidence_cards"] = select_evidence_cards(cards)
        head["has_detail"] = has_detail(head["evidence_cards"])
        # what the status rows quote: the leading treatment's evidence
        head["evidence"] = cards[0] if cards else {}
        out.append(head)
    return out


def sort_cited_by(rows: list[JsonDict]) -> list[JsonDict]:
    """DOM order: severity, then newest first. Each row also carries its
    rank under every column the header can sort by."""
    rows = sorted(rows, key=lambda r: r["citing_date_filed"], reverse=True)
    rows = sorted(rows, key=lambda r: severity_rank(r["severity"]))
    _stamp_ranks(
        rows,
        {
            "severity_index": lambda r: (
                severity_rank(r["severity"]),
                _desc(r["citing_date_filed"]),
            ),
            "recency_index": lambda r: _desc(r["citing_date_filed"]),
            "name_index": lambda r: _name_key(r["citing_case_name"]),
            "mentions_index": lambda r: -(r.get("citing_n_mentions") or 0),
        },
    )
    return rows


# ── Status rows ─────────────────────────────────────────────────────────
# The status rows and the home page's severity filters read the Cited By
# rows pill by pill, through the same helpers. A pill is a direct-history
# act on this case when its treatment, applied or "as recognized by", is
# a direct-history label; every other pill is a citing-reference
# treatment.
Act = tuple[JsonDict, JsonDict]  # (row, pill)


def _row_pills(row: JsonDict) -> list[JsonDict]:
    """A row's pills (group_cited_by), or the row itself as one pill."""
    pills = (row.get("applied") or []) + (row.get("recognized") or [])
    return pills or [
        {"treatment": row["treatment"], "severity": row["severity"]}
    ]


def _is_direct(pill: JsonDict) -> bool:
    """Whether a pill is a direct-history act, in either form."""
    return base_treatment(pill["treatment"]) in DIRECT_HISTORY_TREATMENTS


def _acts(rows: list[JsonDict], direct: bool) -> list[Act]:
    """Every (row, pill) on the rows that is a direct-history act (or,
    with `direct` false, a citing-reference treatment), worst first. At
    equal severity a court's own act comes before another's report of
    one, then the rows' own order (newest first) decides."""
    pairs = [
        (r, p) for r in rows for p in _row_pills(r) if _is_direct(p) == direct
    ]
    return sorted(
        pairs,
        key=lambda rp: (
            severity_rank(rp[1]["severity"]),
            is_recognized(rp[1]["treatment"]),
        ),
    )


def _later_courts(rows: list[JsonDict]) -> list[Act]:
    """One act per citing opinion that treats this case as an authority:
    its worst citing-reference pill, worst opinion first."""
    worst: dict[int, Act] = {}
    for r, p in _acts(rows, direct=False):
        worst.setdefault(r["citing_cluster_id"], (r, p))
    return list(worst.values())


def cited_by_severities(
    cited_by_sorted: list[JsonDict],
) -> dict[str, str | None]:
    """The worst direct-history and citing-reference tiers among a page's
    Cited By rows, for the home page's severity filters; the same acts
    the status rows show (home_status)."""
    appeals = _acts(cited_by_sorted, direct=True)
    later = _later_courts(cited_by_sorted)
    return {
        "dh_severity": appeals[0][1]["severity"] if appeals else None,
        "cr_severity": later[0][1]["severity"] if later else None,
    }


def _passage(row: JsonDict) -> JsonDict:
    """What a status row links to: the citing opinion's Authorities row
    for this case, with the quote as the fallback target."""
    evidence = row.get("evidence") or {}
    return {
        "quote": evidence.get("quote", ""),
        "quote_status": evidence.get("quote_status", ""),
        "authority_n": row.get("citing_authority_n"),
    }


def home_status(opinion_data: JsonDict) -> JsonDict:
    """The "On appeal" and "Later courts" rows: what happened to the case
    on appeal, and the worst later treatment with counts. `scope` says
    what the counts cover: every controlling citing opinion (the anchors)
    or only the opinions in the collection."""
    rows = opinion_data["cited_by"]
    appeals = _acts(rows, direct=True)
    later = _later_courts(rows)
    negative = [(r, p) for r, p in later if p["severity"] in NEGATIVE_TIERS]
    scope = opinion_data.get("cited_by_scope", "controlling")
    populated = opinion_data.get("cited_by_populated")
    # every opinion on the site had its citations extracted, so the
    # citing set within the collection is complete even when the
    # controlling set was never fetched: no row means none, not unknown
    later_known = populated or scope == "collection"
    on_appeal: JsonDict
    if appeals:
        d, pill = appeals[0]
        on_appeal = {
            "state": "treated",
            "treatment": pill["treatment"],
            "severity": pill["severity"],
            "citing_name": d["citing_case_name"],
            "citing_cluster_id": d["citing_cluster_id"],
            **_passage(d),
        }
    elif opinion_data["is_court_of_last_resort"]:
        on_appeal = {"state": "not_reviewable"}
    else:
        on_appeal = {"state": "none" if populated else "unknown"}
    later_courts: JsonDict
    if negative:
        w, pill = negative[0]
        later_courts = {
            "state": "negative",
            "treatment": pill["treatment"],
            "severity": pill["severity"],
            "citing_name": w["citing_case_name"],
            "citing_cluster_id": w["citing_cluster_id"],
            "n_other_negative": len(negative) - 1,
            "n_plain": len(later) - len(negative),
            "n_total": len(later),
            **_passage(w),
        }
    elif later:
        later_courts = {"state": "plain", "n_total": len(later)}
    else:
        later_courts = {"state": "none" if later_known else "unknown"}
    return {
        "scope": scope,
        "on_appeal": on_appeal,
        "later_courts": later_courts,
    }


def docket_numbers(docket: str | None) -> list[str]:
    """A docket field split into its numbers ("11-393, 11-398" → two
    entries), so the templates can clamp it like a citation list."""
    return [d.strip() for d in re.split(r"[,;]\s*", docket or "") if d.strip()]


def search_text(case_name: str, citations: list[str]) -> str:
    """What the search box matches a card against: name and citations,
    letters and digits only, so "103 F.3d 888" and "103f3d888" agree."""
    joined = " ".join([case_name or ""] + list(citations or []))
    return re.sub(r"[^a-z0-9]+", "", joined.lower())


# ── The builder ─────────────────────────────────────────────────────────
class SiteBuilder:
    """Turns a DataSource into the per-opinion and site-wide JSON."""

    def __init__(self, ds: DataSource) -> None:
        self.ds = ds
        self.index = ds.opinion_index
        self.scoped_ids = ds.scoped_ids
        # how many derived edges the validator dropped or flagged
        self.edge_notes = {"temporal": 0, "hierarchy": 0}
        self._streams: dict[int, list[list[str]]] = {}
        self.cited_by_by_cluster = self._collect_cited_by()
        self.history = AppellateHistory(ds, self.cited_by_by_cluster)

    # ── edges → Cited By rows ────────────────────────────────────────
    def _collect_cited_by(self) -> dict[int, list[JsonDict]]:
        """Cited By rows per scoped cluster, from every edge. An edge the
        dates rule out is a mis-linked citation and is dropped; a
        court-hierarchy oddity is kept, with a note, since the citing
        opinion's Authorities tab shows the treatment either way."""
        cited_by: dict[int, list[JsonDict]] = {}
        for idx, edge in enumerate(self.ds.edges):
            try:
                validate_edge(edge, self.index, self.ds.court_level)
            except HierarchyError as exc:
                if exc.kind == "temporal":
                    self.edge_notes["temporal"] += 1
                    continue
                self.edge_notes["hierarchy"] += 1
            cited = edge["cited_cluster_id"]
            if cited in self.scoped_ids:
                cited_by.setdefault(cited, []).append(
                    self._cited_by_view(edge, idx)
                )
        return cited_by

    def _streams_for(self, cluster_id: int) -> list[list[str]]:
        """Token streams of an opinion's text, cached, for quote checks."""
        if cluster_id not in self._streams:
            doc = self.index[cluster_id].get("document_text")
            self._streams[cluster_id] = (
                document_token_streams(doc) if isinstance(doc, list) else []
            )
        return self._streams[cluster_id]

    def _court_fields(self, record: JsonDict) -> JsonDict:
        return {
            **record,
            "court_display": self.ds.court_display.get(
                record["court"], record["court"]
            ),
            "court_level": self.ds.court_level.get(record["court"]),
        }

    def _cited_by_view(self, edge: JsonDict, edge_idx: int) -> JsonDict:
        """The cited side's view of an edge. The quote is widened to its
        sentences in the citing opinion, verified against that text and
        checked for naming this case."""
        citing = self._court_fields(self.index[edge["citing_cluster_id"]])
        cited = self.index[edge["cited_cluster_id"]]
        treatment = edge["treatment"]
        citing_doc = citing.get("document_text")
        quote = edge.get("quote") or ""
        if quote and isinstance(citing_doc, list):
            quote = expand_quote(citing_doc, quote)
        quote_status = quote_names = ""
        if quote:
            quote_status = verify_quote(
                self._streams_for(edge["citing_cluster_id"]), quote
            )["status"]
            quote_names = quote_names_case(
                quote,
                list(cited.get("citations") or []),
                cited.get("case_name") or "",
            )
        rationale = edge.get("rationale") or ""
        return {
            "evidence": {
                "quote": quote,
                "rationale": rationale,
                "quote_status": quote_status,
                "quote_names": quote_names,
            },
            "has_detail": bool(quote or rationale) and has_evidence(treatment),
            "row_id": f"cb-{edge_idx}",
            "citing_cluster_id": citing["cluster_id"],
            # the citing opinion's Authorities row for this case
            "citing_authority_n": edge.get("authority_n"),
            "citing_n_mentions": edge.get("n_mentions") or 0,
            "acting_case": edge.get("acting_case") or "",
            "citing_case_name": citing["case_name"],
            "citing_docket_numbers": docket_numbers(
                citing.get("docket_number")
            ),
            "citing_citations": citing["citations"],
            "citing_court_display": citing["court_display"],
            "citing_date_filed": citing["date_filed"],
            "citing_date_short": short_date(citing["date_filed"]),
            "search_text": search_text(
                citing["case_name"], citing["citations"]
            ),
            "is_scoped": citing["cluster_id"] in self.scoped_ids,
            "treatment": treatment,
            "severity": severity_for(treatment),
            "direction": direction_for(treatment),
            "source": edge.get("source", "model"),
            "expert_treatment": edge.get("expert_treatment"),
        }

    # ── Authorities rows ─────────────────────────────────────────────
    def _authority_page_url(self, group: JsonDict) -> str:
        """The authority's own page when the site has it, else ""."""
        cluster_id = group.get("cited_cluster_id")
        return (
            f"/opinion/{cluster_id}/" if cluster_id in self.scoped_ids else ""
        )

    def _authority_row(self, group: JsonDict, document: Any) -> JsonDict:
        """One Authorities-tab row from a citation group: the pipeline's
        row plus what the template needs to render and sort it. Quotes are
        widened to the sentence(s) containing them."""
        treatment = group.get("treatment") or "Cited by"
        # the docket number is known only for cases in the collection
        cited = self.index.get(group.get("cited_cluster_id") or -1) or {}
        recognized = [
            {
                **r,
                "label": recognizes_label(r.get("treatment") or ""),
                "quote": expand_quote(document, r.get("quote") or ""),
            }
            for r in group.get("recognized") or []
        ]
        recognized.sort(key=lambda x: severity_rank(x.get("severity")))
        recognized_tiers = [x.get("severity") or "Neutral" for x in recognized]
        row = {
            **group,
            "treatment": treatment,
            "is_scoped": group.get("cited_cluster_id") in self.scoped_ids,
            "page_url": self._authority_page_url(group),
            "docket_numbers": docket_numbers(cited.get("docket_number")),
            "search_text": search_text(
                group.get("name") or "",
                list(group.get("cited_as") or [])
                + list(group.get("citations") or []),
            ),
            "treatment_active": to_active_voice(treatment),
            "quote": expand_quote(document, group.get("quote") or ""),
            "recognized": recognized,
            "appearance_index": group["n"] - 1,
            "row_id": f"auth-{group['n']}",
            # has_detail and evidence_cards are set by _cited_authorities
            "recognized_severity": worst_tier(recognized_tiers),
            "recognized_filter": worst_tier(recognized_tiers, default="none"),
        }
        row["overall_severity"] = worst_tier(
            [row.get("severity") or "Neutral", *recognized_tiers]
        )
        return row

    def _authority_cards(
        self, row: JsonDict, streams: list[list[str]]
    ) -> list[JsonDict]:
        """Evidence cards for an expanded Authorities row: this opinion's
        own treatment first, then each treatment it recognizes, by
        severity within each; every quote checked against the text. The
        same rule as the Cited By tab picks which cards are shown
        (select_evidence_cards)."""
        direct = row["treatment"] in DIRECT_HISTORY_TREATMENTS
        applied_shown = has_evidence(row["treatment"])
        cards: list[JsonDict] = [
            {
                "treatment": row["treatment"],
                "order": 0 if direct else 1,
                "severity": row.get("severity") or "Neutral",
                "label": row["treatment_active"],
                "other_label": row.get("treatment_other_label") or "",
                "rationale": row.get("rationale") or "",
                "quote": row.get("quote") or "",
            }
        ]
        for i, x in enumerate(row["recognized"]):
            # a recognition without its own rationale borrows the row's,
            # which on a merely-cited row explains the recognition
            borrowed = (
                row.get("rationale") if (i == 0 and not applied_shown) else ""
            )
            cards.append(
                {
                    "treatment": recognized_form(x.get("treatment") or ""),
                    "order": 2,
                    "severity": x.get("severity") or "Neutral",
                    "label": recognizes_label(x.get("treatment") or ""),
                    "other_label": "",
                    "rationale": x.get("rationale") or borrowed or "",
                    "quote": x.get("quote") or "",
                }
            )
        cards = select_evidence_cards(cards)
        cards.sort(key=lambda c: (c["order"], severity_rank(c["severity"])))
        cites = list(row.get("cited_as") or []) + list(
            row.get("citations") or []
        )
        for card in cards:
            card["quote_status"] = card["quote_names"] = ""
            if card["quote"]:
                card["quote_status"] = verify_quote(streams, card["quote"])[
                    "status"
                ]
                card["quote_names"] = quote_names_case(
                    card["quote"], cites, row.get("name") or ""
                )
        return cards

    @staticmethod
    def _validate_authority_row(row: JsonDict) -> None:
        """Expert validation per pill: the applied pill and each recognized
        pill carry their own mark; the row's state feeds the filter."""
        pills = [
            {
                "kind": "applied",
                "treatment": row["treatment"],
                "severity": row.get("severity") or "Neutral",
            }
        ] + [
            {
                "kind": "recognized",
                "treatment": x.get("treatment") or "",
                "severity": x.get("severity") or "Neutral",
            }
            for x in row["recognized"]
        ]
        states = validate_pills(pills, row.get("expert_treatment") or "")
        row["applied_validation"] = states[0]
        for x, state in zip(row["recognized"], states[1:], strict=True):
            x["validation"] = state
        row["validation"] = row_validation(states)

    def _cited_authorities(self, opinion: JsonDict) -> list[JsonDict]:
        """The Authorities tab: one row per citation group, in DOM order
        (this opinion's own treatment, then what it recognizes, then
        appearance), with ranks for every other sort column."""
        document = opinion["document_text"]
        streams = (
            document_token_streams(document)
            if isinstance(document, list)
            else []
        )
        # an opinion citing its own earlier decision is not an authority
        rows = [
            self._authority_row(g, document)
            for g in opinion.get("citation_groups") or []
            if g.get("cited_cluster_id") != opinion["cluster_id"]
        ]
        for row in rows:
            row["evidence_cards"] = self._authority_cards(row, streams)
            row["has_detail"] = has_detail(row["evidence_cards"])
            self._validate_authority_row(row)
        rows.sort(
            key=lambda r: (
                severity_rank(r.get("severity")),
                severity_rank(r["recognized_severity"]),
                r["n"],
            )
        )
        _stamp_ranks(
            rows,
            {
                "severity_index": lambda r: (
                    severity_rank(r["overall_severity"]),
                    severity_rank(r.get("severity")),
                    severity_rank(r["recognized_severity"]),
                    r["n"],
                ),
                "date_index": lambda r: _desc(r.get("date_filed_iso") or ""),
                "name_index": lambda r: _name_key(r["name"]),
                "mentions_index": lambda r: -(r.get("n_mentions") or 0),
            },
        )
        return rows

    # ── pages ────────────────────────────────────────────────────────
    def build_opinion(self, opinion: JsonDict) -> JsonDict:
        """Everything one opinion page renders."""
        cid = opinion["cluster_id"]
        cited_authorities = self._cited_authorities(opinion)
        # the citations in the text carry their row's severity, name and
        # page, so the rows are built first
        group_info = {r["n"]: r for r in cited_authorities} or None
        body_html, sections = render_body_html(
            opinion["document_text"], self.scoped_ids, group_info
        )
        cited_by = sort_cited_by(
            group_cited_by(list(self.cited_by_by_cluster.get(cid, [])))
        )
        tier = opinion.get("tier", "anchor")
        data = {
            "cluster_id": cid,
            "tier": tier,
            "cl_url": CL_OPINION_URL.format(cluster_id=cid),
            "case_name": opinion["case_name"],
            "name_missing": opinion.get("name_missing", False),
            "docket_number": opinion["docket_number"],
            "docket_numbers": docket_numbers(opinion["docket_number"]),
            "citations": opinion["citations"],
            "court": opinion["court"],
            "court_display": self.ds.court_display.get(
                opinion["court"], opinion["court"]
            ),
            "is_court_of_last_resort": opinion["court"]
            in self.ds.courts_of_last_resort,
            "date_filed": opinion["date_filed"],
            "excerpt": excerpt_from_text(opinion["document_text"]),
            "disposition": disposition_label(opinion.get("disposition")),
            "document": {"body_html": body_html, "sections": sections},
            "cited_authorities": cited_authorities,
            # whether each tab's data was collected, so an empty tab means
            # "none" rather than "not done yet"
            "authorities_populated": bool(opinion.get("citation_groups_meta")),
            "cited_by_populated": tier == "anchor" or bool(cited_by),
            # "controlling": every citing opinion from a court that binds
            # this one; "collection": only the opinions on the site
            "cited_by_scope": "controlling"
            if tier == "anchor"
            else "collection",
            "citing_counts": opinion.get("citing_counts"),
            "cited_by": cited_by,
            "summary": cited_by_severities(cited_by),
            "appellate_history": self.history.graph(cid),
        }
        data["status"] = home_status(data)
        return data

    @staticmethod
    def index_entry(opinion_data: JsonDict) -> JsonDict:
        """The home page card."""
        return {
            "status": opinion_data["status"],
            "tier": opinion_data["tier"],
            "cluster_id": opinion_data["cluster_id"],
            "case_name": opinion_data["case_name"],
            "search_text": search_text(
                opinion_data["case_name"], opinion_data["citations"]
            ),
            "excerpt": opinion_data["excerpt"],
            "name_missing": opinion_data["name_missing"],
            "docket_numbers": opinion_data["docket_numbers"],
            "citations": opinion_data["citations"],
            "court": opinion_data["court"],
            "court_display": opinion_data["court_display"],
            "date_filed": opinion_data["date_filed"],
            "summary": opinion_data["summary"],
        }


# ── Output ──────────────────────────────────────────────────────────────
def _write(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def scope_counts(
    entries: list[JsonDict], pages: list[JsonDict], n_courts: int
) -> JsonDict:
    """What the About page says the site holds, with ready-to-print forms
    so the template carries no number formatting."""
    anchors = [e for e in entries if e["tier"] == "anchor"]
    years = sorted(e["date_filed"][:4] for e in anchors if e["date_filed"])
    scope: JsonDict = {
        "opinions": len(entries),
        "anchors": len(anchors),
        "authorities": sum(1 for e in entries if e["tier"] == "authority"),
        "citing": sum(1 for e in entries if e["tier"] == "citing"),
        "courts": n_courts,
        "authority_rows": sum(len(p["cited_authorities"]) for p in pages),
        "citing_rows": sum(len(p["cited_by"]) for p in pages),
        "citing_rows_at_anchor": sum(
            len(p["cited_by"]) for p in pages if p["tier"] == "anchor"
        ),
        "anchor_earliest_year": years[0] if years else "",
        "anchor_latest_year": years[-1] if years else "",
    }
    for key in (
        "opinions",
        "authorities",
        "citing",
        "authority_rows",
        "citing_rows",
        "citing_rows_at_anchor",
    ):
        scope[f"{key}_display"] = f"{scope[key]:,}"
    return scope


def write_site(ds: DataSource, out_dir: Path = OUT_DIR) -> JsonDict:
    """Build every page and write the `_data/` files. Returns the scope
    counts."""
    opinions_out = out_dir / "opinions"
    opinions_out.mkdir(parents=True, exist_ok=True)
    for stale in opinions_out.glob("*.json"):
        stale.unlink()
    builder = SiteBuilder(ds)
    pages = []
    entries = []
    for opinion in ds.opinions:
        data = builder.build_opinion(opinion)
        _write(opinions_out / f"{data['cluster_id']}.json", data)
        pages.append(data)
        entries.append(builder.index_entry(data))
    # newest first, alphabetical within a date, unnamed opinions last
    entries.sort(key=lambda e: e["case_name"].lower())
    entries.sort(key=lambda e: e["date_filed"] or "", reverse=True)
    entries.sort(key=lambda e: e["name_missing"])
    _write(out_dir / "index.json", entries)

    courts = court_list(ds)
    scope = scope_counts(entries, pages, len(courts))
    _write(out_dir / "scope.json", scope)
    _write(out_dir / "flags.json", FLAGS)
    _write(out_dir / "courts.json", courts)
    _write(
        out_dir / "court_picker.json",
        court_picker_tabs(ds, (c["key"] for c in courts)),
    )
    _write(
        out_dir / "court_categories.json",
        [
            {
                "key": cat,
                "display": ds.category_display[cat],
                "jurisdiction": ds.category_jurisdiction.get(cat),
                "order": idx,
            }
            for idx, cat in enumerate(ds.category_order)
            if cat in ds.category_display
        ],
    )
    _write(
        out_dir / "court_jurisdictions.json",
        [
            {"key": jur, "display": ds.jurisdiction_display[jur], "order": idx}
            for idx, jur in enumerate(ds.jurisdiction_order)
            if jur in ds.jurisdiction_display
        ],
    )
    _write(out_dir / "treatments.json", treatment_table())
    _write(out_dir / "treatment_definitions.json", definition_lookup())

    print(
        f"Wrote {len(pages)} opinion pages and {len(entries)} index entries to {out_dir}"
    )
    print(f"Flags: {FLAGS}")
    print(f"Validated {len(ds.edges)} edges")
    notes = builder.edge_notes
    if notes["temporal"] or notes["hierarchy"]:
        print(
            f"  {notes['temporal']} dropped (dates rule the citation out), "
            f"{notes['hierarchy']} kept with a court-hierarchy warning"
        )
    return scope


def main() -> None:
    write_site(load_data_source())


if __name__ == "__main__":
    main()
