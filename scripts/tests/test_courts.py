from __future__ import annotations

from courts import court_list, court_picker_tabs, court_state
from data_source import DataSource


def test_court_state(chain_source: DataSource) -> None:
    assert court_state(chain_source, "cand") == "California"
    assert court_state(chain_source, "cal") == "California"
    assert court_state(chain_source, "ca9") == ""
    assert court_state(chain_source, "scotus") == ""


def test_court_list_orders_by_level_then_name(
    chain_source: DataSource,
) -> None:
    keys = [c["key"] for c in court_list(chain_source)]
    assert keys == ["scotus", "ca9", "cal", "cand"]


def test_picker_tabs_group_by_state_highest_first(
    chain_source: DataSource,
) -> None:
    tabs = court_picker_tabs(chain_source, ["scotus", "ca9", "cand", "cal"])
    by_key = {t["key"]: t for t in tabs}
    assert list(by_key) == ["federal_appellate", "federal_district", "state"]
    federal = by_key["federal_appellate"]
    assert [g["name"] for g in federal["groups"]] == [
        "U.S. Supreme Court",
        "U.S. Circuit courts",
    ]
    california = by_key["state"]["groups"][0]
    assert california["name"] == "California"
    assert [c["key"] for c in california["courts"]] == ["cal"]
    assert by_key["federal_district"]["groups"][0]["courts"][0]["depth"] == 0


def test_picker_puts_unclassified_courts_in_other(
    chain_source: DataSource,
) -> None:
    tabs = court_picker_tabs(chain_source, ["scotus", "unknown"])
    assert tabs[-1]["key"] == "other"
    assert tabs[-1]["groups"][0]["keys"] == ["unknown"]
