"""The site's data, read from `data-source/`.

Folders and files, all optional except the anchors:

    anchor_opinions/{cluster_id}.json   the anchor opinions
    authorities/{cluster_id}.json       cases the anchors cite
    citing_opinions/{cluster_id}.json   controlling opinions citing an anchor
    citing_opinions_round2/…            a second citing set, same shape
    centralia/{cluster_id}.json         a PDF re-read of the opinion; used
                                        when `used` is true
    citation_groups/{cluster_id}.json   citation extraction output: the
                                        writings' html, one group per cited
                                        case, kept/removed spans, added
                                        mentions
    treatments/{cluster_id}.json        the citator's treatment per group
                                        (`treatments`), plus `disposition`,
                                        `on_appeal`, expert `gold`
    cited_metadata.json                 metadata for cited clusters
    citing_counts_*.json                how often cited opinions are cited
    citing_edges.csv, citing_edges_round2.csv
                                        the citing opinions fetched for
                                        each anchor (the citing scope)

An opinion payload holds `cluster_id`, `case_name`, `docket_number`,
`citations`, `court`, `court_full_name`, `court_jurisdiction`, `date_filed`
and `opinions`: one entry per writing with `id`, `type`, `author`, `html`.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from cl_html import citation_map, cluster_to_document_text
from data_source import DataSource, JsonDict, short_date
from model_output import clean_authority_name, is_case_group

DATA_SOURCE = Path(__file__).parent.parent / "data-source"
# payload folders in load order, with the tier their opinions belong to
PAYLOAD_DIRS: tuple[tuple[str, str], ...] = (
    ("anchor_opinions", "anchor"),
    ("authorities", "authority"),
    ("citing_opinions", "citing"),
    ("citing_opinions_round2", "citing"),
)
CITING_COUNTS_FILES = (
    "citing_counts_authorities.json",
    "citing_counts_citing.json",
)
CITING_EDGES_FILES = ("citing_edges.csv", "citing_edges_round2.csv")

# Hand-written names for the anchors' courts; every other court is named
# from its payload's court_full_name and classified from its CourtListener
# jurisdiction code.
COURT_DISPLAY: dict[str, str] = {
    "scotus": "Supreme Court of the United States",
    "ca2": "Court of Appeals for the Second Circuit",
    "cadc": "Court of Appeals for the D.C. Circuit",
    "ord": "District Court, D. Oregon",
    "cand": "District Court, N.D. California",
    "lactapp": "Louisiana Court of Appeal",
    "michctapp": "Michigan Court of Appeals",
    "nysurct": "New York Surrogate's Court",
    "mesuperct": "Maine Superior Court",
}
# lower = higher court
COURT_LEVEL: dict[str, int] = {
    "scotus": 0,
    "ca1": 1, "ca2": 1, "ca3": 1, "ca4": 1, "ca5": 1, "ca6": 1, "ca7": 1,
    "ca8": 1, "ca9": 1, "ca10": 1, "ca11": 1, "cadc": 1, "cafc": 1,
    "ord": 2, "cand": 2, "lactapp": 2, "michctapp": 2,
    "nysurct": 3, "mesuperct": 3,
}  # fmt: skip
COURT_CATEGORY: dict[str, str] = {
    "scotus": "scotus",
    "ca1": "circuit", "ca2": "circuit", "ca3": "circuit", "ca4": "circuit",
    "ca5": "circuit", "ca6": "circuit", "ca7": "circuit", "ca8": "circuit",
    "ca9": "circuit", "ca10": "circuit", "ca11": "circuit",
    "cadc": "circuit", "cafc": "circuit",
    "ord": "district", "cand": "district",
    "lactapp": "state_appellate", "michctapp": "state_appellate",
    "nysurct": "state_trial", "mesuperct": "state_trial",
}  # fmt: skip
COURTS_OF_LAST_RESORT = frozenset({"scotus"})
CATEGORY_DISPLAY: dict[str, str] = {
    "scotus": "U.S. Supreme Court",
    "circuit": "U.S. Circuit courts",
    "district": "U.S. District courts",
    "state_supreme": "State COLR",
    "state_appellate": "State appellate courts",
    "state_trial": "State trial courts",
}
CATEGORY_ORDER: tuple[str, ...] = (
    "scotus", "circuit", "district",
    "state_supreme", "state_appellate", "state_trial",
)  # fmt: skip
CATEGORY_JURISDICTION: dict[str, str] = {
    "scotus": "federal",
    "circuit": "federal",
    "district": "federal",
    "state_supreme": "state",
    "state_appellate": "state",
    "state_trial": "state",
}
JURISDICTION_DISPLAY: dict[str, str] = {"federal": "Federal", "state": "State"}
JURISDICTION_ORDER: tuple[str, ...] = ("federal", "state")
# CourtListener jurisdiction code → (category, level, court of last resort)
JURISDICTION_CLASS: dict[str, tuple[str, int, bool]] = {
    "F": ("circuit", 1, False),
    "FD": ("district", 2, False),
    "FB": ("district", 2, False),
    "FBP": ("district", 2, False),
    "FS": ("district", 2, False),
    "S": ("state_supreme", 1, True),
    "SA": ("state_appellate", 2, False),
    "ST": ("state_trial", 3, False),
    "SS": ("state_trial", 3, False),
    "SAG": ("state_trial", 3, False),
}
DEFAULT_CLASS = ("state_trial", 3, False)


def _cite_key(text: str) -> str:
    """A citation reduced to letters and digits, pin cite dropped."""
    return re.sub(r"[^a-z0-9]+", "", text.split(",")[0].lower())


def _short_name(name: str) -> str:
    """The first party of a case name, reduced to letters and digits."""
    return re.sub(
        r"[^a-z0-9]+",
        "",
        re.split(r"\s+v\.?\s+", name or "", maxsplit=1)[0].lower(),
    )


class ClusterResolver:
    """Resolves a citation group to an opinion in the collection the way a
    citator's citation table is built: by the cluster id the extraction
    attached, else by a shared reporter citation (the opinion's own
    citations plus any known from the cited-case metadata), else by the
    first party's name when only one opinion in the collection has it."""

    def __init__(
        self,
        opinions: list[JsonDict],
        extra_citations: dict[int, list[str]] | None = None,
    ) -> None:
        self.ids = {op["cluster_id"] for op in opinions}
        self.by_cite: dict[str, int] = {}
        names: dict[str, set[int]] = {}
        for op in opinions:
            cid = op["cluster_id"]
            cites = list(op.get("citations") or []) + list(
                (extra_citations or {}).get(cid) or []
            )
            for c in cites:
                self.by_cite.setdefault(_cite_key(c), cid)
            name = _short_name(op.get("case_name") or "")
            if len(name) >= 5:
                names.setdefault(name, set()).add(cid)
        # a name shared by several decisions (a case's trial, appellate
        # and final opinions) identifies none of them
        self.by_name = {
            n: next(iter(ids)) for n, ids in names.items() if len(ids) == 1
        }

    def resolve(self, group: JsonDict) -> int | None:
        cluster = group.get("cited_cluster_id")
        if cluster:
            return int(cluster)
        forms = (group.get("citations") or []) + (group.get("cited_as") or [])
        for c in forms:
            hit = self.by_cite.get(_cite_key(c))
            if hit:
                return hit
        return self.by_name.get(
            _short_name(group.get("name") or group.get("cl_name") or "")
        )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path, default: Any) -> Any:
    return _read_json(path) if path.exists() else default


def display_case_name(rec: JsonDict) -> str:
    """The case name, or a name built from the citation or docket number
    when the record has none, so every opinion has something to show."""
    name = (rec.get("case_name") or "").strip()
    if name:
        return name
    cites = rec.get("citations") or []
    if cites:
        return f"Unnamed opinion ({cites[0]})"
    docket = (rec.get("docket_number") or "").strip()
    if docket:
        return f"Unnamed opinion (No. {docket})"
    return "Unnamed opinion"


class Loader:
    """Reads `data-source/` into a DataSource."""

    def __init__(self, root: Path = DATA_SOURCE) -> None:
        self.root = root
        self.centralia_dir = root / "centralia"
        self.groups_dir = root / "citation_groups"
        self.treatments_dir = root / "treatments"
        self.court_display = dict(COURT_DISPLAY)
        self.court_level = dict(COURT_LEVEL)
        self.court_category = dict(COURT_CATEGORY)
        self.courts_of_last_resort = set(COURTS_OF_LAST_RESORT)
        self.cited_meta: dict[str, JsonDict] = _read_json_if_exists(
            root / "cited_metadata.json", {}
        )
        self.citing_counts: dict[str, JsonDict] = {}
        for name in CITING_COUNTS_FILES:
            self.citing_counts.update(
                _read_json_if_exists(root / name, {}).get("per_authority", {})
            )

    # ── courts ───────────────────────────────────────────────────────
    def register_court(self, rec: JsonDict) -> None:
        """Make a payload's court known to the display, category and
        level maps (no-op for courts listed by hand)."""
        court = rec["court"]
        self.court_display.setdefault(
            court,
            rec.get("court_full_name") or rec.get("court_short_name") or court,
        )
        if court in self.court_category:
            return
        if court == "scotus":
            category, level, last_resort = "scotus", 0, True
        else:
            category, level, last_resort = JURISDICTION_CLASS.get(
                rec.get("court_jurisdiction") or "", DEFAULT_CLASS
            )
        self.court_category[court] = category
        self.court_level[court] = level
        if last_resort:
            self.courts_of_last_resort.add(court)

    # ── per-cluster files ────────────────────────────────────────────
    def centralia_writings(self, cluster_id: int) -> list[JsonDict] | None:
        data = _read_json_if_exists(
            self.centralia_dir / f"{cluster_id}.json", None
        )
        if not data or not data.get("used") or not data.get("opinions"):
            return None
        writings: list[JsonDict] = data["opinions"]
        return writings

    def citation_groups(
        self, cluster_id: int, cl_html_texts: list[str]
    ) -> JsonDict | None:
        """The citation pipeline's export for a cluster, joined with its
        treatments and cited-case metadata: the writings to render, the
        converter state, the Authorities rows and the tab's meta."""
        path = self.groups_dir / f"{cluster_id}.json"
        if not path.exists():
            return None
        data = _read_json(path)
        cite_map = citation_map(cl_html_texts)
        tdata = _read_json_if_exists(
            self.treatments_dir / f"{cluster_id}.json", {}
        )
        treatments = tdata.get("treatments", {})
        gold = tdata.get("gold", {})
        groups_by_gid: dict[str, JsonDict] = {}
        rows: list[JsonDict] = []
        for g in data["groups"]:
            # statutes, articles and unattached "Id."s are not authorities;
            # left out of the converter state too, so their spans render
            # as plain text
            if not is_case_group(g):
                continue
            cluster = g.get("cited_cluster_id")
            cl_name = g.get("cl_name", "")
            if not cluster:
                # link a group with no cluster id through its reporter cites
                for c in g.get("citations", []):
                    hit = cite_map.get(c) or cite_map.get(
                        c.split(",")[0].strip()
                    )
                    if hit:
                        cluster, cl_name = int(hit[0]), (cl_name or hit[1])
                        break
            meta = self.cited_meta.get(str(cluster), {}) if cluster else {}
            citations = g.get("citations") or []
            name = (
                g.get("name")
                or meta.get("case_name")
                or cl_name
                or (citations[0] if citations else "")
            )
            name = clean_authority_name(name)
            groups_by_gid[g["gid"]] = {
                "n": g["n"],
                "name": name,
                "cluster": cluster,
            }
            # every form this opinion cites the case as, in reading order
            forms = [f for f in (g.get("cited_as") or citations) if f != name]
            t = treatments.get(str(g["n"])) or {}
            rows.append(
                {
                    "n": g["n"],
                    "expert_treatment": (gold.get(str(g["n"])) or {}).get(
                        "final", ""
                    ),
                    "treatment": t.get("applied") or "Cited by",
                    "severity": t.get("severity") or "Neutral",
                    "direction": t.get("direction") or "Citing Reference",
                    "treatment_other_label": t.get("other_label") or "",
                    "quote": t.get("quote") or "",
                    "rationale": t.get("rationale") or "",
                    "recognized": t.get("recognized") or [],
                    "source": "model",
                    "name": name,
                    "cited_cluster_id": cluster,
                    "cited_as": forms,
                    "n_mentions": g.get("n_mentions", 0),
                    "date_filed": short_date(meta.get("date_filed")),
                    "date_filed_iso": meta.get("date_filed") or "",
                    "status": meta.get("status", ""),
                    "court_name": meta.get("court_name", ""),
                    "citations": meta.get("citations", []),
                }
            )
        rows.sort(key=lambda r: r["n"])
        return {
            "opinions": data["opinions"],
            "state": {
                "occurrences": data["occurrences"],
                "manual": data.get("manual", []),
                "groups": groups_by_gid,
            },
            "rows": rows,
            "disposition": tdata.get("disposition"),
            "on_appeal": tdata.get("on_appeal", []),
            "meta": {
                "n_authorities": len(rows),
                "n_mentions": sum(r["n_mentions"] for r in rows),
            },
        }

    def opinion_record(self, path: Path, tier: str) -> JsonDict:
        """One scoped opinion from its payload file."""
        rec = _read_json(path)
        self.register_court(rec)
        cl_htmls = [o["html"] for o in rec["opinions"]]
        grouped = self.citation_groups(rec["cluster_id"], cl_htmls)
        if grouped:
            writings, cite_map, state = (
                grouped["opinions"],
                None,
                grouped["state"],
            )
        else:
            centralia = self.centralia_writings(rec["cluster_id"])
            writings = centralia or rec["opinions"]
            # a PDF re-read resolves no citations: carry CourtListener's
            # resolved reporter cites over by string match
            cite_map = citation_map(cl_htmls) if centralia else None
            state = None
        return {
            "cluster_id": rec["cluster_id"],
            "tier": tier,
            "opinion_ids": [
                o["id"]
                for o in rec["opinions"]
                if isinstance(o.get("id"), int)
            ],
            "citing_counts": self.citing_counts.get(str(rec["cluster_id"])),
            "case_name": display_case_name(rec),
            "name_missing": not (rec.get("case_name") or "").strip(),
            "docket_number": rec.get("docket_number") or "",
            "citations": rec.get("citations") or [],
            "court": rec["court"],
            "date_filed": rec["date_filed"],
            "document_text": cluster_to_document_text(
                writings, cite_map, state
            ),
            "citation_groups": grouped["rows"] if grouped else [],
            "citation_groups_meta": grouped["meta"] if grouped else {},
            "disposition": grouped["disposition"] if grouped else None,
            "on_appeal": grouped["on_appeal"] if grouped else [],
        }

    def opinions(self) -> list[JsonDict]:
        """Every payload, anchors first; a cluster present in several
        folders is loaded once, with the first folder's tier."""
        anchor_dir = self.root / PAYLOAD_DIRS[0][0]
        if not anchor_dir.exists():
            raise SystemExit(
                f"{anchor_dir} is missing. Copy the anchor payloads into "
                "data-source/ first (see README § Data)."
            )
        paths: list[tuple[Path, str]] = []
        seen: set[int] = set()
        for name, tier in PAYLOAD_DIRS:
            folder = self.root / name
            if not folder.exists():
                continue
            for path in sorted(
                folder.glob("*.json"), key=lambda p: int(p.stem)
            ):
                if int(path.stem) not in seen:
                    seen.add(int(path.stem))
                    paths.append((path, tier))
        return [self.opinion_record(path, tier) for path, tier in paths]

    # ── edges ────────────────────────────────────────────────────────
    def controlling_pairs(
        self, opinions: list[JsonDict]
    ) -> set[tuple[int, int]]:
        """(citing, cited) pairs from the citing-scope CSVs: the citing
        opinions fetched for each anchor. An anchor may be named by a
        writing's opinion id or by its cluster id."""
        to_cluster: dict[int, int] = {}
        for op in opinions:
            if op["tier"] != "anchor":
                continue
            to_cluster[op["cluster_id"]] = op["cluster_id"]
            for oid in op["opinion_ids"]:
                to_cluster[oid] = op["cluster_id"]
        pairs: set[tuple[int, int]] = set()
        for name in CITING_EDGES_FILES:
            path = self.root / name
            if not path.exists():
                continue
            with path.open(encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    anchor = r.get("anchor_opinion_id") or r.get(
                        "anchor_cluster_id"
                    )
                    cited = to_cluster.get(int(anchor)) if anchor else None
                    if cited:
                        pairs.add((int(r["citing_cluster_id"]), cited))
        return pairs

    def resolve_groups(self, opinions: list[JsonDict]) -> None:
        """Give every citation group that names an opinion in the
        collection that opinion's cluster id, so both tabs are built from
        the same links."""
        extra = {
            int(cid): m.get("citations") or []
            for cid, m in self.cited_meta.items()
            if str(cid).isdigit()
        }
        resolver = ClusterResolver(opinions, extra)
        for op in opinions:
            for row in op.get("citation_groups") or []:
                cluster = resolver.resolve(row)
                if cluster in resolver.ids:
                    row["cited_cluster_id"] = cluster

    @staticmethod
    def edges(
        opinions: list[JsonDict], controlling: set[tuple[int, int]]
    ) -> list[JsonDict]:
        """The citation table: one edge per (citing, cited) pair of
        opinions in the collection, read off the citing opinion's
        authority rows, with the mention count and the treatment the
        citing opinion applied. A treatment the citing opinion only
        reports rides along as its own "as recognized by" edge. `scope` is
        "controlling" for pairs in the citing scope (every such citing
        opinion was fetched) and "collection" otherwise."""
        scoped = {op["cluster_id"] for op in opinions}
        edges: list[JsonDict] = []
        seen: set[tuple[int, int]] = set()
        for op in opinions:
            citing = op["cluster_id"]
            for row in op.get("citation_groups") or []:
                cited = row.get("cited_cluster_id")
                if not cited or cited == citing or cited not in scoped:
                    continue
                common = {
                    "citing_cluster_id": citing,
                    "cited_cluster_id": cited,
                    "scope": "controlling"
                    if (citing, cited) in controlling
                    else "collection",
                    "authority_n": row.get("n"),
                    "n_mentions": row.get("n_mentions") or 0,
                }
                if (citing, cited) not in seen:
                    seen.add((citing, cited))
                    edges.append(
                        {
                            **common,
                            "source": row.get("source") or "model",
                            "expert_treatment": row.get("expert_treatment")
                            or None,
                            "treatment": row.get("treatment") or "Cited by",
                            "quote": row.get("quote") or "",
                            "rationale": row.get("rationale") or "",
                        }
                    )
                for rec in row.get("recognized") or []:
                    base = (rec.get("treatment") or "").strip()
                    if not base.endswith(" by"):
                        continue
                    edges.append(
                        {
                            **common,
                            "source": "model",
                            "expert_treatment": None,
                            "treatment": base.replace(
                                " by", " as recognized by"
                            ),
                            "quote": rec.get("quote") or "",
                            "rationale": rec.get("rationale") or "",
                            # the court the citing opinion says acted
                            "acting_case": (
                                rec.get("acting_case") or ""
                            ).strip(),
                        }
                    )
        return edges

    def load(self) -> DataSource:
        opinions = self.opinions()
        self.resolve_groups(opinions)
        return DataSource(
            opinions=opinions,
            edges=self.edges(opinions, self.controlling_pairs(opinions)),
            court_display=self.court_display,
            court_level=self.court_level,
            court_category=self.court_category,
            courts_of_last_resort=frozenset(self.courts_of_last_resort),
            category_display=CATEGORY_DISPLAY,
            category_order=CATEGORY_ORDER,
            category_jurisdiction=CATEGORY_JURISDICTION,
            jurisdiction_display=JURISDICTION_DISPLAY,
            jurisdiction_order=JURISDICTION_ORDER,
        )


def load() -> DataSource:
    """Read `data-source/` into a DataSource."""
    return Loader().load()
