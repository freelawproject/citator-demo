"""The History tab: a case's route through the court system.

The graph for an opinion is the whole chain it belongs to, so every
decision in a case draws the same picture and only the "This opinion"
marker moves. Nodes are decisions; edges run from the decision acted on to
the court that acted and carry the treatments recorded for it. Nodes come
from three places: direct-history treatments between opinions on the site,
each opinion's own account of the decision it reviewed when the site does
not hold that decision, and acts a later opinion only reports ("Vacated
and remanded as recognized by …").

The result places nodes on a grid: one column per court level, lowest
court on the left and highest on the right, and one row per decision in
time order, newest at the top, with a connector row between each pair of
decision rows. The connector joins each decision to the one before it in
time, so the route reads as one unbroken path; what each court did is
written on its card, and the path shows to which decision.
"""

from __future__ import annotations

from typing import Any

from data_source import DataSource, JsonDict
from model_output import (
    act_verbs,
    below_entry,
    canonical_court,
    disposition_treatment,
    names_supreme_court,
)
from taxonomy import (
    DIRECT_HISTORY_TREATMENTS,
    base_treatment,
    direction_for,
    is_recognized,
    past_tense,
    severity_for,
    severity_rank,
    to_active_voice,
)

UNKNOWN_LEVEL = 99
LOWEST_LEVEL = 4
# grid column of the lowest court; column 1 holds the time axis, 2 a spacer
FIRST_COURT_COLUMN = 3

Link = dict[str, Any]
Node = dict[str, Any]
Edge = dict[str, Any]


def _link(treatment: str, severity: str, quote: str, text: str = "") -> Link:
    """One act on an edge. A disposition the taxonomy has no label for is
    "Ordered by" and carries the court's own sentence as `text`."""
    return {
        "treatment": treatment,
        "severity": severity,
        "quote": quote,
        "text": text,
    }


def _labels(links: list[Link], own: bool) -> list[dict[str, str]]:
    """What a card says that decision did: a pill in the active voice
    ("Reversing"); an order with no label is the "Ordered" pill, which
    opens the court's own sentence (`text`). `defined_as` is the label
    whose definition the pill shows, written from the page's side: the
    active form on the page's own card, the past form ("Reversed") on any
    other card, where the page's case is the one acted on."""
    return [
        {
            "treatment": to_active_voice(lk["treatment"]),
            "defined_as": (
                to_active_voice(lk["treatment"])
                if own
                else lk["treatment"].removesuffix(" by")
            ),
            "severity": lk["severity"],
            "text": lk["text"],
        }
        for lk in links
    ]


class AppellateHistory:
    """Builds the History tab's graph for any opinion on the site.

    Construction indexes the direct-history edges in both directions and
    the direct-history acts later opinions only report; `graph(cid)` then
    assembles and lays out one opinion's chain.
    """

    def __init__(
        self, ds: DataSource, cited_by_by_cluster: dict[int, list[JsonDict]]
    ) -> None:
        self.ds = ds
        self.index = ds.opinion_index
        # cited → citing → links, and citing → cited → links
        self.above: dict[int, dict[int, list[Link]]] = {}
        self.below: dict[int, dict[int, list[Link]]] = {}
        # decision → direct-history acts a later opinion reports on it
        self.reported: dict[int, list[JsonDict]] = {}
        self._index_direct_history(ds.edges)
        self._index_reported(cited_by_by_cluster)

    # ── indexes ────────────────────────────────────────────────────────
    def _index_direct_history(self, edges: list[JsonDict]) -> None:
        for edge in edges:
            if direction_for(edge["treatment"]) != "Direct History":
                continue
            link = _link(
                edge["treatment"],
                severity_for(edge["treatment"]),
                edge.get("quote") or "",
            )
            citing, cited = edge["citing_cluster_id"], edge["cited_cluster_id"]
            self.above.setdefault(cited, {}).setdefault(citing, []).append(
                link
            )
            self.below.setdefault(citing, {}).setdefault(cited, []).append(
                link
            )

    def _index_reported(
        self, cited_by_by_cluster: dict[int, list[JsonDict]]
    ) -> None:
        for cluster_id, rows in cited_by_by_cluster.items():
            for row in rows:
                treatment = row["treatment"]
                if not is_recognized(treatment):
                    continue
                if base_treatment(treatment) not in DIRECT_HISTORY_TREATMENTS:
                    continue
                self.reported.setdefault(cluster_id, []).append(
                    {
                        "treatment_past": past_tense(treatment),
                        "severity": row["severity"],
                        "quote": (row.get("evidence") or {}).get("quote", ""),
                        "acting_case": (row.get("acting_case") or "").strip(),
                        "citing_cluster_id": row["citing_cluster_id"],
                        "citing_case_name": row["citing_case_name"],
                        "citing_date_filed": row["citing_date_filed"],
                        "is_scoped": row["is_scoped"],
                    }
                )

    # ── nodes ──────────────────────────────────────────────────────────
    def _opinion_node(self, cluster_id: int, role: str) -> Node:
        op = self.index[cluster_id]
        return {
            "role": role,  # self | above | below
            "cluster_id": cluster_id,
            "case_name": op["case_name"],
            "court": self.ds.court_display.get(op["court"], op["court"]),
            "court_id": op["court"],
            "level": self.ds.court_level.get(op["court"], UNKNOWN_LEVEL),
            "date_filed": op["date_filed"],
            # shown behind the card's "Details" toggle
            "docket_number": op.get("docket_number") or "",
            "citations": op.get("citations") or [],
            "url": f"/opinion/{cluster_id}/",
        }

    def _column_label(self, level: int, members: list[Node]) -> str:
        """What to call one rung. The level alone is not enough: a state
        supreme court and a federal court of appeals share one."""
        courts = [n["court_id"] for n in members if n.get("court_id")]
        if level == 0:
            return "Highest court"
        if level == 1:
            if courts and all(
                c in self.ds.courts_of_last_resort for c in courts
            ):
                return "Court of last resort"
            return "Appellate court"
        if (
            level == 2
            and courts
            and all(
                self.ds.court_category.get(c) == "state_appellate"
                for c in courts
            )
        ):
            return "Intermediate appellate court"
        return "Trial court"

    # ── the graph ──────────────────────────────────────────────────────
    def graph(self, cid: int) -> JsonDict:
        """Nodes, edges and grid layout for the chain `cid` belongs to."""
        builder = _GraphBuilder(self, cid)
        builder.add_connected_opinions()
        builder.add_recorded_edges()
        builder.add_decisions_below()
        builder.add_reported_acts()
        return builder.layout()


class _GraphBuilder:
    """Assembles one opinion's chain, step by step, then lays it out."""

    def __init__(self, history: AppellateHistory, cid: int) -> None:
        self.h = history
        self.cid = cid
        self.nodes: list[Node] = []
        self.edges: list[Edge] = []
        self.index_of: dict[Any, int] = {}
        self.self_at = self._add(history._opinion_node(cid, "self"), cid)

    def _add(self, node: Node, key: Any) -> int:
        self.nodes.append(node)
        self.index_of[key] = len(self.nodes) - 1
        return self.index_of[key]

    def _opinion_indexes(self) -> list[tuple[int, int]]:
        return [
            (k, at) for k, at in self.index_of.items() if isinstance(k, int)
        ]

    def add_connected_opinions(self) -> None:
        """Every opinion joined to this one by direct history, reached in
        both directions through every neighbour. The role records which
        side it was reached from, which places an undated decision."""
        role_of: dict[int, str] = {}
        for graph, role in ((self.h.below, "below"), (self.h.above, "above")):
            queue, reached = [self.cid], {self.cid}
            while queue:
                node = queue.pop(0)
                for neighbour in sorted(graph.get(node, {})):
                    if neighbour in reached:
                        continue
                    reached.add(neighbour)
                    role_of.setdefault(neighbour, role)
                    queue.append(neighbour)
        for cluster_id in sorted(role_of):
            self._add(
                self.h._opinion_node(cluster_id, role_of[cluster_id]),
                cluster_id,
            )

    def add_recorded_edges(self) -> None:
        """One edge per recorded pair, so a remand loop keeps both links."""
        for cluster_id, at in self._opinion_indexes():
            for lower, links in (self.h.below.get(cluster_id) or {}).items():
                if lower not in self.index_of:
                    continue
                self.edges.append(
                    {
                        "actor": at,
                        "target": self.index_of[lower],
                        "links": sorted(
                            links, key=lambda x: severity_rank(x["severity"])
                        ),
                    }
                )

    def add_decisions_below(self) -> None:
        """For every decision with nothing recorded below it, the decision
        it says it reviewed, as a node the site has no page for. The link
        carries the opinion's disposition (model_output.disposition_treatment);
        with none recorded it is drawn but says nothing."""
        for cluster_id, at in self._opinion_indexes():
            if any(e["actor"] == at for e in self.edges):
                continue
            record = self.h.index.get(cluster_id) or {}
            entry = below_entry(record)
            if entry is None:
                continue
            disposition = disposition_treatment(record.get("disposition"))
            key = ("below", entry.get("court") or "", entry.get("name") or "")
            below = self.index_of.get(key)
            if below is None:
                below = self._add(
                    {
                        "role": "below",
                        "cluster_id": None,
                        "url": "",
                        "case_name": entry.get("name") or "",
                        "court": entry.get("court") or "",
                        "date_filed": "",
                    },
                    key,
                )
            links = (
                [
                    _link(
                        disposition["treatment"],
                        disposition["severity"],
                        entry.get("quote") or "",
                        disposition["text"],
                    )
                ]
                if disposition
                else []
            )
            self.edges.append({"actor": at, "target": below, "links": links})

    def _collect_reports(self) -> dict[tuple[int, int], JsonDict]:
        """Reported acts per (decision, reporting opinion), skipping acts a
        recorded edge already carries for that decision."""
        reported: dict[tuple[int, int], JsonDict] = {}
        for cluster_id, at in self._opinion_indexes():
            on_record = [
                act_verbs(lk["treatment"].removesuffix(" by"))
                for e in self.edges
                if e["target"] == at
                for lk in e["links"]
            ]
            for row in self.h.reported.get(cluster_id) or []:
                label = row["treatment_past"]
                if any(act_verbs(label) <= recorded for recorded in on_record):
                    continue
                link = _link(f"{label} by", row["severity"], row["quote"])
                key = (at, row["citing_cluster_id"])
                event = reported.get(key)
                if event:
                    known = {
                        lk["treatment"].removesuffix(" by")
                        for lk in event["links"]
                    }
                    if label not in known:
                        event["links"].append(link)
                        event["links"].sort(
                            key=lambda lk: severity_rank(lk["severity"])
                        )
                    continue
                acting_id, acting_name = canonical_court(
                    self.h.ds.court_display, row["acting_case"]
                )
                reported[key] = {
                    "target": at,
                    "links": [link],
                    "node": {
                        "role": "reported",
                        "cluster_id": None,
                        "case_name": row["citing_case_name"],
                        "acting_case": row["acting_case"],
                        "court": acting_name or "Court not identified",
                        "court_id": acting_id,
                        # the report cannot precede the act, so the reporting
                        # opinion's date places it in time
                        "date_filed": row["citing_date_filed"],
                        "url": (
                            f"/opinion/{row['citing_cluster_id']}/"
                            if row["is_scoped"]
                            else ""
                        ),
                    },
                }
        return reported

    def add_reported_acts(self) -> None:
        """One card per reporting opinion, each reported act drawn once: an
        act already drawn for a decision is not drawn again, and an opinion
        reporting the same act against two of the case's decisions has it
        drawn from the earlier decision only."""
        reported = self._collect_reports()
        drawn: set[tuple[int, str]] = set()
        cards: dict[tuple[str, str], dict[str, Any]] = {}
        ordered = sorted(
            reported.items(),
            key=lambda kv: (
                kv[1]["node"]["date_filed"],
                self.nodes[kv[0][0]].get("date_filed") or "",
            ),
        )
        for (at, reporter), entry in ordered:
            # the same decision can sit in the source data twice (same name,
            # same day), so a reporting opinion is keyed by name and date
            who = (entry["node"]["case_name"], entry["node"]["date_filed"])
            card = cards.get(who)
            links = [
                lk
                for lk in entry["links"]
                if (at, lk["treatment"]) not in drawn
                and (card is None or lk["treatment"] not in card["labels"])
            ]
            if not links:
                continue
            if card is None:
                card = cards[who] = {
                    "idx": self._add(entry["node"], f"reported:{reporter}"),
                    "labels": set(),
                }
            card["labels"].update(lk["treatment"] for lk in links)
            drawn.update((at, lk["treatment"]) for lk in links)
            self.edges.append(
                {"actor": card["idx"], "target": at, "links": links}
            )

    # ── layout ─────────────────────────────────────────────────────────
    def _place_unknown_levels(self) -> None:
        """A node with no opinion behind it is placed from its neighbours:
        a decision below sits one level under the decision that reviewed
        it; a reported act sits one level above the decision it concerns,
        or at the top when the text names the U.S. Supreme Court."""
        for node in self.nodes:
            if node.get("level", UNKNOWN_LEVEL) < UNKNOWN_LEVEL:
                continue
            at = self.nodes.index(node)
            if node["role"] == "reported":
                if names_supreme_court(
                    f"{node.get('acting_case', '')} {node.get('court', '')}"
                ):
                    node["level"] = 0
                    continue
                targets = [
                    self.nodes[e["target"]]
                    for e in self.edges
                    if e["actor"] == at
                ]
                known = [
                    t["level"]
                    for t in targets
                    if t.get("level", UNKNOWN_LEVEL) < UNKNOWN_LEVEL
                ]
                node["level"] = max(min(known) - 1, 0) if known else 0
            else:
                actors = [
                    self.nodes[e["actor"]]
                    for e in self.edges
                    if e["target"] == at
                ]
                known = [
                    a["level"]
                    for a in actors
                    if a.get("level", UNKNOWN_LEVEL) < UNKNOWN_LEVEL
                ]
                node["level"] = (
                    min(max(known) + 1, LOWEST_LEVEL)
                    if known
                    else LOWEST_LEVEL
                )

    def _sequence(self) -> list[int]:
        """Node indexes in time order. An undated decision below came
        first; any other undated node is placed last."""

        def when(i: int) -> str:
            node = self.nodes[i]
            return node.get("date_filed") or (
                "" if node["role"] == "below" else "9999"
            )

        return sorted(range(len(self.nodes)), key=when)

    def layout(self) -> JsonDict:
        """Grid placement: columns by court level (lowest court first),
        rows by time (newest first), and for each card what it did and
        the connector reaching it."""
        nodes, edges = self.nodes, self.edges
        if len(nodes) == 1:
            return {"steps": nodes, "chain": [], "levels": [], "n_opinions": 1}
        self._place_unknown_levels()
        sequence = self._sequence()
        for edge in edges:
            if not edge["links"]:
                continue
            actor = nodes[edge["actor"]]
            actor.setdefault("acts", []).append(
                {
                    "treatments": _labels(
                        edge["links"], own=actor["role"] == "self"
                    )
                }
            )
        # court columns: the time axis takes column 1 and a spacer column
        # 2; the lowest court sits in column 3, the highest at the right
        level_numbers = sorted({n["level"] for n in nodes}, reverse=True)
        levels = [
            {
                "level": lv,
                "col": FIRST_COURT_COLUMN + i,
                "label": self.h._column_label(
                    lv, [n for n in nodes if n["level"] == lv]
                ),
            }
            for i, lv in enumerate(level_numbers)
        ]
        # two rungs can share a name; the one to the left is the lower one
        for lower, upper in zip(levels, levels[1:], strict=False):
            if lower["label"] == upper["label"]:
                lower["label"] = "Lower court"
        col_of = {lv["level"]: lv["col"] for lv in levels}
        tier_of = {lv["level"]: lv["label"] for lv in levels}
        # decision rows: odd rows, newest at the top, a connector row
        # between each pair
        n = len(sequence)
        row_of = {i: (n - 1 - pos) * 2 + 1 for pos, i in enumerate(sequence)}
        previous = {
            i: sequence[pos - 1] for pos, i in enumerate(sequence) if pos
        }
        chain = [
            self._step(nodes[i], i, row_of, col_of, tier_of, previous.get(i))
            for i in sequence
        ]
        return {
            "steps": nodes,
            "chain": chain,
            "levels": levels,
            "has_reported": any(n["role"] == "reported" for n in nodes),
            "n_opinions": sum(1 for n in nodes if n["cluster_id"]),
        }

    def _step(
        self,
        node: Node,
        i: int,
        row_of: dict[int, int],
        col_of: dict[int, int],
        tier_of: dict[int, str],
        previous: int | None,
    ) -> JsonDict:
        """One card: its grid cell and the connector from the decision
        before it in time: an elbow in the row below the card, running
        from the previous decision's column to this court's. What the
        card did (`acts`) is already on the node."""
        row, col = row_of[i], col_of[node["level"]]
        links = []
        if previous is not None:
            prev_col = col_of[self.nodes[previous]["level"]]
            if col > prev_col:
                direction = "up"
            elif col < prev_col:
                direction = "down"
            else:
                direction = "same"
            links.append(
                {
                    "dir": direction,
                    "row": row + 1,
                    "col_start": min(prev_col, col),
                    "col_end": max(prev_col, col) + 1,
                    "span": abs(col - prev_col) + 1,
                }
            )
        return {
            **node,
            "index": i,
            "row": row,
            "col": col,
            "tier": tier_of[node["level"]],
            "acts": node.get("acts") or [],
            "links": links,
        }
