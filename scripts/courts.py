"""Court lists for the templates: the sorted court list and the home
page's court picker.

The picker has a tab per jurisdiction and level. Inside a tab, courts are
grouped by the state they sit in (federal district courts included), each
group ordered highest court first. Federal appellate courts belong to no
state and are grouped by category instead.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from data_source import DataSource

PICKER_TABS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("federal_appellate", "Federal appellate", ("scotus", "circuit")),
    ("federal_district", "Federal district", ("district",)),
    ("state", "State", ("state_supreme", "state_appellate", "state_trial")),
)

STATE_NAMES: tuple[str, ...] = (
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virgin Islands", "Virginia",
    "Washington", "West Virginia", "Wisconsin", "Wyoming", "Puerto Rico",
    "Guam", "Northern Mariana Islands", "American Samoa",
)  # fmt: skip

# Reporter abbreviations of the states. "N.D." / "S.D." are left out: in
# a court name they read as a district, and both Dakotas' courts spell
# their state in full.
STATE_ABBREVIATIONS: dict[str, str] = {
    "Ala.": "Alabama", "Ariz.": "Arizona", "Ark.": "Arkansas",
    "Cal.": "California", "Colo.": "Colorado", "Conn.": "Connecticut",
    "Del.": "Delaware", "D.C.": "District of Columbia", "Fla.": "Florida",
    "Ga.": "Georgia", "Haw.": "Hawaii", "Ill.": "Illinois",
    "Ind.": "Indiana", "Kan.": "Kansas", "Ky.": "Kentucky", "La.": "Louisiana",
    "Me.": "Maine", "Md.": "Maryland", "Mass.": "Massachusetts",
    "Mich.": "Michigan", "Minn.": "Minnesota", "Miss.": "Mississippi",
    "Mo.": "Missouri", "Mont.": "Montana", "Neb.": "Nebraska",
    "Nev.": "Nevada", "N.H.": "New Hampshire", "N.J.": "New Jersey",
    "N.M.": "New Mexico", "N.Y.": "New York", "N.C.": "North Carolina",
    "Okla.": "Oklahoma", "Or.": "Oregon",
    "Pa.": "Pennsylvania", "R.I.": "Rhode Island", "S.C.": "South Carolina",
    "Tenn.": "Tennessee", "Tex.": "Texas",
    "Vt.": "Vermont", "Va.": "Virginia", "Wash.": "Washington",
    "W. Va.": "West Virginia", "Wis.": "Wisconsin", "Wyo.": "Wyoming",
    "P.R.": "Puerto Rico",
}  # fmt: skip

# Courts whose display name names no state, or names the wrong one.
COURT_STATE: dict[str, str] = {
    "dcd": "District of Columbia",
}

# The circuits read in their own order, not alphabetically.
CIRCUIT_ORDER: dict[str, int] = {
    "ca1": 1, "ca2": 2, "ca3": 3, "ca4": 4, "ca5": 5, "ca6": 6, "ca7": 7,
    "ca8": 8, "ca9": 9, "ca10": 10, "ca11": 11, "cadc": 12, "cafc": 13,
}  # fmt: skip

OTHER_GROUP = "Other courts"


def court_state(ds: DataSource, key: str) -> str:
    """The state a court sits in, read off its display name; "" for the
    federal appellate courts."""
    if key in COURT_STATE:
        return COURT_STATE[key]
    if ds.court_category.get(key) in ("scotus", "circuit"):
        return ""
    name = ds.court_display.get(key, key)
    # longest first so "West Virginia" wins over "Virginia"
    for state in sorted(STATE_NAMES, key=len, reverse=True):
        if state in name:
            return state
    for abbrev in sorted(STATE_ABBREVIATIONS, key=len, reverse=True):
        if abbrev in name:
            return STATE_ABBREVIATIONS[abbrev]
    return ""


def _display(ds: DataSource, key: str) -> str:
    return ds.court_display.get(key, key)


def court_list(ds: DataSource) -> list[dict[str, Any]]:
    """Every court in scope, by hierarchy level then name."""
    return sorted(
        (
            {
                "key": key,
                "display": ds.court_display.get(key, key),
                "level": ds.court_level.get(key, 99),
                "category": ds.court_category.get(key, "other"),
            }
            for key in ds.court_display
        ),
        key=lambda c: (c["level"], c["display"].lower()),
    )


def _court_entry(ds: DataSource, key: str, depth: int) -> dict[str, Any]:
    return {
        "key": key,
        "display": ds.court_display.get(key, key),
        "level": ds.court_level.get(key, 99),
        "depth": depth,
    }


def _group(ds: DataSource, name: str, keys: list[str]) -> dict[str, Any]:
    """One picker group, its courts highest first and indented by their
    rank among the levels present in the group."""
    courts = sorted(
        keys,
        key=lambda k: (
            ds.court_level.get(k, 99),
            CIRCUIT_ORDER.get(k, 99),
            _display(ds, k).lower(),
        ),
    )
    levels = sorted({ds.court_level.get(k, 99) for k in courts})
    return {
        "name": name,
        "keys": courts,
        "courts": [
            _court_entry(ds, k, levels.index(ds.court_level.get(k, 99)))
            for k in courts
        ],
    }


def court_picker_tabs(
    ds: DataSource, court_keys: Iterable[str]
) -> list[dict[str, Any]]:
    """The picker's structure: tabs of groups of courts (see module doc).
    Courts no tab claims land in a final "Other" tab."""
    keys = set(court_keys)
    tabs: list[dict[str, Any]] = []
    for tab_key, tab_display, categories in PICKER_TABS:
        in_tab = [
            k for k in keys if ds.court_category.get(k, "other") in categories
        ]
        if not in_tab:
            continue
        by_group: dict[str, list[str]] = {}
        for key in in_tab:
            if tab_key == "federal_appellate":
                group = ds.category_display[ds.court_category[key]]
            else:
                group = court_state(ds, key) or OTHER_GROUP
            by_group.setdefault(group, []).append(key)
        groups = [
            _group(ds, name, by_group[name])
            for name in sorted(by_group, key=lambda g: (g == OTHER_GROUP, g))
        ]
        if tab_key == "federal_appellate":
            display_order = [
                ds.category_display.get(c, "") for c in ds.category_order
            ]
            groups.sort(key=lambda g: display_order.index(g["name"]))
        tabs.append(
            {
                "key": tab_key,
                "display": tab_display,
                "n_courts": len(in_tab),
                "groups": groups,
            }
        )
    placed = {c["key"] for t in tabs for g in t["groups"] for c in g["courts"]}
    leftover = sorted(keys - placed, key=lambda k: _display(ds, k).lower())
    if leftover:
        tabs.append(
            {
                "key": "other",
                "display": "Other",
                "n_courts": len(leftover),
                "groups": [
                    {
                        "name": OTHER_GROUP,
                        "keys": leftover,
                        "courts": [_court_entry(ds, k, 0) for k in leftover],
                    }
                ],
            }
        )
    return tabs
