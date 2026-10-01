"""The contract between a data module and the build.

A data module (`real_data`, `mock_data`) exposes `load() -> DataSource`.
The build reads everything it needs from that object, so the two modules
are interchangeable and neither does any work at import time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class DataSource:
    """Everything the build needs about the opinions and their courts.

    `opinions` are the scoped opinions: one record per cluster with
    `cluster_id`, `case_name`, `docket_number`, `citations`, `court`,
    `date_filed`, `document_text` and, when the citator has run on it,
    `citation_groups`, `citation_groups_meta`, `disposition`, `on_appeal`.
    `edges` are the treatment relationships (citing cluster → cited
    cluster, treatment, quote, rationale); the Authorities and Cited By
    tabs are both derived from them. `external_opinions` holds metadata
    for citing opinions that have no page of their own.
    """

    opinions: list[JsonDict]
    edges: list[JsonDict]
    court_display: dict[str, str]
    court_level: dict[str, int]
    court_category: dict[str, str]
    courts_of_last_resort: frozenset[str]
    category_display: dict[str, str]
    category_order: tuple[str, ...]
    category_jurisdiction: dict[str, str]
    jurisdiction_display: dict[str, str]
    jurisdiction_order: tuple[str, ...]
    external_opinions: dict[int, JsonDict] = field(default_factory=dict)

    @property
    def scoped_ids(self) -> frozenset[int]:
        """Cluster ids that have a page on the site."""
        return frozenset(op["cluster_id"] for op in self.opinions)

    @property
    def opinion_index(self) -> dict[int, JsonDict]:
        """Every known opinion, scoped or external, by cluster id."""
        index = {op["cluster_id"]: op for op in self.opinions}
        index.update(self.external_opinions)
        return index


def short_date(iso: str | None) -> str:
    """2012-06-28 → 06/28/2012, the form the tab columns use."""
    if not iso:
        return ""
    parts = iso.split("-")
    if len(parts) != 3:
        return iso
    year, month, day = parts
    return f"{month}/{day}/{year}"
