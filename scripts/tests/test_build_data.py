from __future__ import annotations

import json
from pathlib import Path

import pytest

import mock_data
from build_data import (
    HierarchyError,
    SiteBuilder,
    docket_numbers,
    group_cited_by,
    home_status,
    search_text,
    sort_cited_by,
    validate_edge,
    write_site,
)
from data_source import DataSource
from real_data import ClusterResolver, Loader


def row(citing: int, treatment: str, date: str, **extra: object) -> dict:
    return {
        "citing_cluster_id": citing,
        "citing_case_name": f"Case {citing}",
        "citing_date_filed": date,
        "treatment": treatment,
        "severity": {
            "Cited by": "Neutral",
            "Distinguished by": "Caution",
            "Overruled as recognized by": "Stop",
            "Affirmed by": "Positive",
        }[treatment],
        "direction": (
            "Related Reference"
            if "recognized" in treatment
            else "Direct History"
            if treatment == "Affirmed by"
            else "Citing Reference"
        ),
        "evidence": {"quote": "q", "rationale": "r"},
        **extra,
    }


def test_group_cited_by_merges_one_citing_opinion() -> None:
    rows = [
        row(1, "Cited by", "2020-01-01"),
        row(1, "Overruled as recognized by", "2020-01-01"),
        row(2, "Distinguished by", "2019-01-01"),
    ]
    grouped = {g["citing_cluster_id"]: g for g in group_cited_by(rows)}
    one = grouped[1]
    # the row speaks with its own applied treatment, but its severity is
    # the worst of everything it carries
    assert one["treatment"] == "Cited by"
    assert one["severity"] == "Stop"
    assert [p["treatment_past"] for p in one["recognized"]] == ["Overruled"]
    assert one["recognized_filter"] == "Stop"
    # only negative treatments get an evidence card
    assert [c["label"] for c in one["evidence_cards"]] == [
        "Overruled as recognized by"
    ]
    assert grouped[2]["recognized_filter"] == "none"
    assert grouped[2]["has_detail"] is True


def test_cited_by_cards_follow_the_row_order() -> None:
    # the applied treatment comes first even when a recognized one is
    # more severe
    rows = [
        row(1, "Overruled as recognized by", "2020-01-01"),
        row(1, "Distinguished by", "2020-01-01"),
    ]
    (one,) = group_cited_by(rows)
    assert [c["label"] for c in one["evidence_cards"]] == [
        "Distinguished by",
        "Overruled as recognized by",
    ]
    assert one["evidence"]["label"] == "Distinguished by"


def test_sort_cited_by_orders_and_stamps_ranks() -> None:
    rows = group_cited_by(
        [
            row(1, "Cited by", "2020-01-01"),
            row(2, "Distinguished by", "2018-01-01"),
            row(3, "Cited by", "2021-01-01"),
        ]
    )
    out = sort_cited_by(rows)
    assert [r["citing_cluster_id"] for r in out] == [2, 3, 1]
    assert [r["recency_index"] for r in out] == [2, 0, 1]
    assert [r["name_index"] for r in out] == [1, 2, 0]


def test_home_status_states() -> None:
    base = {
        "is_court_of_last_resort": False,
        "cited_by_populated": True,
        "cited_by_scope": "controlling",
    }
    empty = home_status({**base, "cited_by": []})
    assert empty["on_appeal"] == {"state": "none"}
    assert empty["later_courts"] == {"state": "none"}
    unknown = home_status(
        {**base, "cited_by": [], "cited_by_populated": False}
    )
    assert unknown["on_appeal"]["state"] == "unknown"
    colr = home_status(
        {**base, "cited_by": [], "is_court_of_last_resort": True}
    )
    assert colr["on_appeal"]["state"] == "not_reviewable"
    rows = group_cited_by(
        [
            row(1, "Affirmed by", "2020-01-01", citing_authority_n=4),
            row(2, "Distinguished by", "2021-01-01"),
            row(3, "Cited by", "2022-01-01"),
        ]
    )
    treated = home_status({**base, "cited_by": sort_cited_by(rows)})
    assert treated["on_appeal"]["state"] == "treated"
    assert treated["on_appeal"]["authority_n"] == 4
    later = treated["later_courts"]
    assert later["state"] == "negative"
    assert (
        later["treatment"],
        later["n_other_negative"],
        later["n_plain"],
    ) == (
        "Distinguished by",
        0,
        1,
    )


def test_validate_edge(chain_source: DataSource) -> None:
    index = chain_source.opinion_index
    levels = chain_source.court_level
    validate_edge(chain_source.edges[0], index, levels)
    with pytest.raises(HierarchyError) as info:
        validate_edge(
            {
                "citing_cluster_id": 1,
                "cited_cluster_id": 2,
                "treatment": "Cited by",
            },
            index,
            levels,
        )
    assert info.value.kind == "temporal"
    with pytest.raises(HierarchyError) as info:
        validate_edge(
            {
                "citing_cluster_id": 4,
                "cited_cluster_id": 2,
                "treatment": "Affirmed by",
            },
            index,
            levels,
        )
    assert info.value.kind == "hierarchy"


def test_cluster_resolver(chain_source: DataSource) -> None:
    resolver = ClusterResolver(chain_source.opinions, {3: ["99 S. Ct. 1"]})
    assert resolver.resolve({"cited_cluster_id": 3}) == 3
    assert resolver.resolve({"citations": ["2 U.S. 1, 5"]}) == 2
    assert resolver.resolve({"citations": ["99 S. Ct. 1"]}) == 3
    assert resolver.resolve({"name": "People v. Roe"}) == 4
    # "Smith v. Jones" names two decisions in the collection: no match
    assert resolver.resolve({"name": "Smith v. Nobody"}) is None
    assert resolver.resolve({"name": "Nobody v. Anyone"}) is None


def test_edges_come_from_the_authority_rows(chain_source: DataSource) -> None:
    opinions = [dict(op) for op in chain_source.opinions]
    opinions[3]["citation_groups"] = [
        {
            "n": 1,
            "citations": ["2 U.S. 1"],
            "n_mentions": 4,
            "treatment": "Distinguished by",
            "recognized": [{"treatment": "Reversed by", "acting_case": ""}],
        },
        {"n": 2, "cited_cluster_id": 4, "n_mentions": 1},
        {"n": 3, "cited_cluster_id": 999, "n_mentions": 1},
    ]
    Loader().resolve_groups(opinions)
    assert opinions[3]["citation_groups"][0]["cited_cluster_id"] == 2
    edges = Loader.edges(opinions, {(4, 2)})
    assert [
        (e["citing_cluster_id"], e["cited_cluster_id"]) for e in edges
    ] == [
        (4, 2),
        (4, 2),
    ]
    assert edges[0]["n_mentions"] == 4 and edges[0]["scope"] == "controlling"
    assert edges[1]["treatment"] == "Reversed as recognized by"


def test_docket_numbers() -> None:
    assert docket_numbers("No. 11-393, 11-398; 11-400") == [
        "No. 11-393",
        "11-398",
        "11-400",
    ]
    assert docket_numbers("") == []
    assert docket_numbers(None) == []


def test_search_text() -> None:
    assert (
        search_text("Smith v. Jones", ["103 F.3d 888"])
        == "smithvjones103f3d888"
    )


def test_self_citation_is_not_an_authority(chain_source: DataSource) -> None:
    opinion = {
        **chain_source.opinions[1],
        "citation_groups": [
            {
                "n": 1,
                "cited_cluster_id": 2,
                "name": "Smith v. Jones",
                "n_mentions": 1,
            },
            {
                "n": 2,
                "cited_cluster_id": 1,
                "name": "Smith v. Jones",
                "n_mentions": 1,
            },
        ],
        "citation_groups_meta": {"n_authorities": 2},
    }
    page = SiteBuilder(chain_source).build_opinion(opinion)
    assert [a["n"] for a in page["cited_authorities"]] == [2]


def test_builder_pages(chain_source: DataSource) -> None:
    builder = SiteBuilder(chain_source)
    page = builder.build_opinion(chain_source.opinions[1])
    assert page["cl_url"].endswith("/opinion/2/x/")
    assert page["disposition"]["label"] == "Affirmed"
    cited_by = {r["citing_cluster_id"]: r for r in page["cited_by"]}
    assert cited_by[3]["treatment"] == "Reversed by"
    assert cited_by[4]["recognized"][0]["treatment_past"] == "Reversed"
    assert page["summary"] == {"dh_severity": "Stop", "cr_severity": "Stop"}
    assert page["disposition"]["severity"] == "Positive"
    assert page["status"]["on_appeal"]["citing_name"] == "Jones v. Smith"
    assert page["appellate_history"]["n_opinions"] == 3
    entry = builder.index_entry(page)
    assert entry["search_text"].startswith("smithvjones")


def test_write_site_from_fixtures(tmp_path: Path) -> None:
    scope = write_site(mock_data.load(), tmp_path)
    assert scope["opinions"] == 10
    assert len(list((tmp_path / "opinions").glob("*.json"))) == 10
    index = json.loads((tmp_path / "index.json").read_text())
    assert len(index) == 10
    for name in (
        "scope.json",
        "flags.json",
        "courts.json",
        "court_picker.json",
        "court_categories.json",
        "court_jurisdictions.json",
        "treatments.json",
    ):
        assert (tmp_path / name).exists(), name
