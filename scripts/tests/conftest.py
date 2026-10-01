"""Shared fixtures: a small DataSource of three opinions in one appellate
chain, plus two unrelated citing opinions."""

from __future__ import annotations

import pytest

from data_source import DataSource, JsonDict

COURT_DISPLAY = {
    "scotus": "Supreme Court of the United States",
    "ca9": "Court of Appeals for the Ninth Circuit",
    "cand": "District Court, N.D. California",
    "cal": "Supreme Court of California",
}
COURT_LEVEL = {"scotus": 0, "ca9": 1, "cand": 2, "cal": 1}
COURT_CATEGORY = {
    "scotus": "scotus",
    "ca9": "circuit",
    "cand": "district",
    "cal": "state_supreme",
}


def opinion(
    cluster_id: int,
    case_name: str,
    court: str,
    date_filed: str,
    text: str = "A paragraph of text that is long enough to be an excerpt "
    "for the home page, which needs at least one hundred and twenty "
    "characters to count as substantive.",
    **extra: object,
) -> JsonDict:
    return {
        "cluster_id": cluster_id,
        "tier": "anchor",
        "case_name": case_name,
        "docket_number": f"No. {cluster_id}",
        "citations": [f"{cluster_id} U.S. 1"],
        "court": court,
        "date_filed": date_filed,
        "document_text": text,
        **extra,
    }


def edge(citing: int, cited: int, treatment: str, **extra: object) -> JsonDict:
    return {
        "citing_cluster_id": citing,
        "cited_cluster_id": cited,
        "treatment": treatment,
        "quote": "",
        "rationale": "",
        "source": "model",
        "expert_treatment": None,
        **extra,
    }


@pytest.fixture
def chain_source() -> DataSource:
    """District court (1) → Ninth Circuit (2) → Supreme Court (3), plus a
    California opinion (4) that distinguishes the Ninth Circuit decision
    and reports the reversal."""
    opinions = [
        opinion(1, "Smith v. Jones", "cand", "2010-01-01"),
        opinion(
            2,
            "Smith v. Jones",
            "ca9",
            "2011-01-01",
            disposition={
                "label": "Affirmed",
                "text": "The judgment is affirmed.",
            },
        ),
        opinion(
            3,
            "Jones v. Smith",
            "scotus",
            "2012-06-01",
            disposition={"label": "Reversed", "text": "Reversed."},
        ),
        opinion(4, "People v. Doe", "cal", "2013-01-01"),
    ]
    edges = [
        edge(2, 1, "Affirmed by"),
        edge(3, 2, "Reversed by"),
        edge(4, 2, "Distinguished by", quote="We find Smith inapposite."),
        edge(
            4,
            2,
            "Reversed as recognized by",
            acting_case="the United States Supreme Court",
            scope="collection",
        ),
    ]
    return DataSource(
        opinions=opinions,
        edges=edges,
        court_display=COURT_DISPLAY,
        court_level=COURT_LEVEL,
        court_category=COURT_CATEGORY,
        courts_of_last_resort=frozenset({"scotus", "cal"}),
        category_display={
            "scotus": "U.S. Supreme Court",
            "circuit": "U.S. Circuit courts",
            "district": "U.S. District courts",
            "state_supreme": "State COLR",
        },
        category_order=("scotus", "circuit", "district", "state_supreme"),
        category_jurisdiction={
            "scotus": "federal",
            "circuit": "federal",
            "district": "federal",
            "state_supreme": "state",
        },
        jurisdiction_display={"federal": "Federal", "state": "State"},
        jurisdiction_order=("federal", "state"),
    )
