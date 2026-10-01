from __future__ import annotations

from build_data import SiteBuilder
from data_source import DataSource
from history import AppellateHistory


def test_every_opinion_in_a_chain_draws_the_same_graph(
    chain_source: DataSource,
) -> None:
    builder = SiteBuilder(chain_source)
    history = AppellateHistory(chain_source, builder.cited_by_by_cluster)
    graphs = [history.graph(cid) for cid in (1, 2, 3)]
    names = [sorted(s["case_name"] for s in g["steps"]) for g in graphs]
    assert names[0] == names[1] == names[2]
    g = graphs[1]
    assert g["n_opinions"] == 3
    # highest court in the rightmost column, newest decision on the top row
    by_name = {s["case_name"] + s["court"]: s for s in g["chain"]}
    scotus = by_name["Jones v. SmithSupreme Court of the United States"]
    assert scotus["col"] == max(s["col"] for s in g["chain"])
    assert scotus["row"] == 1
    assert [s["cluster_id"] for s in g["chain"]][:3] == [1, 2, 3]
    assert [lv["label"] for lv in g["levels"]] == [
        "Trial court",
        "Appellate court",
        "Highest court",
    ]
    assert scotus["tier"] == "Highest court"
    # the connector comes from the decision before it in time: an elbow in
    # the connector row, climbing to the right
    link = scotus["links"][0]
    assert (link["dir"], link["row"], link["span"]) == ("up", 2, 2)
    oldest = next(s for s in g["chain"] if s["cluster_id"] == 1)
    assert oldest["links"] == []
    # the reversal is recorded, so the California report of it adds no card
    assert g["has_reported"] is False
    self_step = next(s for s in g["chain"] if s["role"] == "self")
    assert self_step["cluster_id"] == 2
    assert self_step["acts"][0]["treatments"][0]["treatment"] == "Affirmed"


def test_decision_below_sits_under_the_court_that_reviewed_it(
    chain_source: DataSource,
) -> None:
    # the trial court decision (1) names the decision it reviewed; seen
    # from the Supreme Court opinion (3) that decision must still sit one
    # level under the trial court, not one level under the Supreme Court
    opinions = [dict(op) for op in chain_source.opinions]
    opinions[0]["on_appeal"] = [
        {"court": "Magistrate", "name": "Smith v. Jones"}
    ]
    opinions[0]["disposition"] = {"label": "Affirmed", "text": ""}
    source = DataSource(**{**chain_source.__dict__, "opinions": opinions})
    builder = SiteBuilder(source)
    graph = builder.history.graph(3)
    below = next(s for s in graph["chain"] if s["role"] == "below")
    trial = next(s for s in graph["chain"] if s["cluster_id"] == 1)
    assert below["col"] < trial["col"]
    assert below["col"] == min(s["col"] for s in graph["chain"])


def test_single_opinion_has_no_chain(chain_source: DataSource) -> None:
    builder = SiteBuilder(chain_source)
    graph = builder.history.graph(4)
    assert graph["chain"] == []
    assert graph["n_opinions"] == 1
