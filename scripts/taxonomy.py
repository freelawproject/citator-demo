"""The treatment taxonomy: labels, severity tiers, directions and the
wording each side of a treatment uses.

A treatment label is written from the cited case's side ("Distinguished
by"). The Authorities tab speaks from the citing opinion's side, so labels
are rewritten to the active voice there ("Distinguishes"). A treatment the
citing opinion only reports another court applying is the "as recognized
by" form ("Overruled as recognized by"); it keeps the severity of the
underlying treatment.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

SEVERITY_BY_TREATMENT: dict[str, str] = {
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
    "Cert. denied by": "Neutral",
    "Cited by": "Neutral",
    # Positive
    "Affirmed by": "Positive",
}

# most serious first; Positive (an affirmance) ranks after Neutral
SEVERITY_ORDER: tuple[str, ...] = (
    "Stop",
    "Warning",
    "Caution",
    "Neutral",
    "Positive",
)
SEVERITY_RANK: dict[str, int] = {
    tier: rank for rank, tier in enumerate(SEVERITY_ORDER)
}
NEGATIVE_TIERS = frozenset({"Stop", "Warning", "Caution"})

# Procedural review of the same case by a higher court.
DIRECT_HISTORY_TREATMENTS = frozenset(
    {
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
)

# Treatments only a higher court, or the same court, can apply.
VERTICAL_OR_SELF_TREATMENTS = DIRECT_HISTORY_TREATMENTS | {
    "Overruled by",
    "Abrogated by",
}

ACTIVE_VOICE: dict[str, str] = {
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

RECOGNIZED_SUFFIX = " as recognized by"

# What each treatment means, shown when a pill is hovered or focused.
# "Acting case" is the opinion applying the treatment, "target case" the
# one receiving it; the About page says so above the treatment table.
DEFINITIONS: dict[str, str] = {
    # Direct History
    "Reversed by": (
        "On direct appeal, the acting case reverses the target court's "
        "decision."
    ),
    "Reversed and remanded by": (
        "On direct appeal, the acting case reverses the target court's "
        "decision and sends the case back to the target court for "
        "further proceedings."
    ),
    "Vacated and remanded by": (
        "On direct appeal, the acting case sets aside the target court's "
        "decision, leaving it without legal effect, and sends the case "
        "back to the target court for further proceedings."
    ),
    "Vacated by": (
        "On direct appeal, the acting case sets aside the target court's "
        "decision, leaving it without legal effect."
    ),
    "Affirmed in part; Reversed in part by": (
        "On direct appeal, the acting case affirms part of the target "
        "case while reversing other parts of it."
    ),
    "Affirmed in part; Vacated in part by": (
        "On direct appeal, the acting case affirms part of the target "
        "case while vacating other parts of it."
    ),
    "Remanded by": (
        "On direct appeal, the acting case sends the case back to the "
        "target court for further proceedings."
    ),
    "Cert. granted by": (
        "On a petition for review, the acting case agrees to hear an "
        "appeal of the target case."
    ),
    "Dismissed by": (
        "On direct appeal, the acting case ends the appeal without "
        "deciding its merits."
    ),
    "Affirmed by": (
        "On direct appeal, the acting case affirms the target court's "
        "decision."
    ),
    "Cert. denied by": (
        "On a petition for review, the acting case refuses to hear an "
        "appeal of the target case."
    ),
    # Citing Reference
    "Overruled by": (
        "The acting case expressly overrules all or part of the target case."
    ),
    "Abrogated by": (
        "The acting case effectively, but not explicitly, overrules all "
        "or part of the target case."
    ),
    "Questioned by": (
        "The acting case questions the continuing validity or "
        "precedential value of the target case, either because another "
        "decision implicitly undermines it or because of intervening "
        "events such as judicial or legislative overruling."
    ),
    "Disapproved by": (
        "The acting case expressly or implicitly disapproves all or part "
        "of the target case for its reasoning or result and reaches a "
        "contrary holding, but does not overrule it."
    ),
    "Limited by": (
        "The acting case narrows the scope or applicability of the "
        "target case rather than extending it or accepting it as "
        "authoritative."
    ),
    "Criticized by": (
        "The acting case criticizes all or part of the target case's "
        "reasoning but, unlike Disapproved, does not reach a contrary "
        "holding, or the criticism is dicta."
    ),
    "Distinguished by": (
        "The acting case reaches a different result because its facts, "
        "procedural posture or law differ from the target case's. "
        "Sometimes also called declined to extend."
    ),
    "Declined to follow by": (
        "The acting case chooses not to apply the reasoning or ruling of "
        "the target case, and no more specific treatment applies."
    ),
    "Cited by": (
        "The acting case cites, references, discusses, interprets, "
        "clarifies or explains the target case without treating it "
        "negatively."
    ),
}

# Labels whose pills show no definition: a plain citation needs none.
NO_TOOLTIP = frozenset({"Cited by"})

# Related Reference: the "X as recognized by" form of any label opens
# with this and continues with the root treatment's definition.
RECOGNIZED_PREFIX = "The citing case notes that "


def recognized_definition(text: str) -> str:
    """ "The acting case overrules…" → "The citing case notes that the
    acting case overrules…"."""
    return RECOGNIZED_PREFIX + text[:1].lower() + text[1:]


def is_recognized(treatment: str) -> bool:
    """Whether the label is the "X as recognized by" form."""
    return RECOGNIZED_SUFFIX in treatment


def base_treatment(treatment: str) -> str:
    """ "Overruled as recognized by" → "Overruled by"; others unchanged."""
    return treatment.replace(RECOGNIZED_SUFFIX, " by")


def past_tense(treatment: str) -> str:
    """ "Overruled as recognized by" / "Overruled by" → "Overruled"."""
    return base_treatment(treatment).removesuffix(" by")


def recognized_form(treatment: str) -> str:
    """ "Overruled by" → "Overruled as recognized by"."""
    return past_tense(treatment) + RECOGNIZED_SUFFIX


def severity_for(treatment: Any) -> str:
    """The severity tier of a treatment label, in either form."""
    if not isinstance(treatment, str):
        return "Other"
    return SEVERITY_BY_TREATMENT.get(base_treatment(treatment), "Other")


def severity_rank(tier: str | None) -> int:
    """Sort key: most severe first, unknown tiers last."""
    return SEVERITY_RANK.get(tier or "", len(SEVERITY_ORDER))


def worst_tier(tiers: Iterable[str | None], default: str = "Neutral") -> str:
    """The most severe tier among `tiers`, or `default` when empty."""
    return min(
        (t or "Neutral" for t in tiers), key=severity_rank, default=default
    )


def direction_for(treatment: str) -> str:
    """Related Reference (recognized), Direct History or Citing Reference."""
    if is_recognized(treatment):
        return "Related Reference"
    if treatment in DIRECT_HISTORY_TREATMENTS:
        return "Direct History"
    return "Citing Reference"


def to_active_voice(treatment: str) -> str:
    """What the citing opinion does: "Distinguished by" → "Distinguishes",
    "Overruled as recognized by" → "Recognizes as overruled"."""
    if treatment in ACTIVE_VOICE:
        return ACTIVE_VOICE[treatment]
    if is_recognized(treatment):
        return f"Recognizes as {past_tense(treatment).lower()}"
    return treatment.removesuffix(" by")


def recognizes_label(treatment: str) -> str:
    """Pill text for a treatment this opinion reports another court
    applied: "Recognizes to be overruled"."""
    return f"Recognizes to be {past_tense(treatment).lower()}"


def validate_pills(pills: list[dict[str, Any]], expert: str) -> list[str]:
    """Validation state for each pill of one row, in order.

    Each pill is {"kind": "applied" | "recognized", "treatment": "X by",
    "severity"}. `expert` is the expert's most negative treatment for the
    pair, in either form, or "" when the pair was not reviewed.

    - "agree": the pill is the expert's label (same kind, same treatment).
    - "disagree": the expert recorded a negative treatment and no pill on
      the row matches it. Marked on the negative pills of the expert's
      kind, or on the applied pill when there are none.
    - "unverified": no expert review; or the expert's label is neutral;
      or an expert "Distinguished by" was read as "Cited by" or "Limited
      by", which is too close a call to present as a disagreement; or
      another pill on a row that already matches.
    """
    if not expert:
        return ["unverified"] * len(pills)
    expert_recognized = is_recognized(expert)
    expert_base = base_treatment(expert)
    states = [
        "agree"
        if (p["kind"] == "recognized") == expert_recognized
        and p["treatment"] == expert_base
        else "unverified"
        for p in pills
    ]
    if "agree" in states or severity_for(expert_base) not in NEGATIVE_TIERS:
        return states
    applied = next((p for p in pills if p["kind"] == "applied"), None)
    if (
        expert_base == "Distinguished by"
        and applied
        and applied["treatment"] in ("Cited by", "Limited by")
    ):
        return states
    kind = "recognized" if expert_recognized else "applied"
    negative = [
        i
        for i, p in enumerate(pills)
        if p["kind"] == kind
        and (p.get("severity") or "Neutral") in NEGATIVE_TIERS
    ]
    if not negative:
        negative = [i for i, p in enumerate(pills) if p["kind"] == "applied"][
            :1
        ] or [0]
    for i in negative:
        states[i] = "disagree"
    return states


def row_validation(states: list[str]) -> str:
    """One state for a whole row: any disagreement invalidates it, else
    any agreement validates it, else it is unverified."""
    if "disagree" in states:
        return "disagree"
    if "agree" in states:
        return "agree"
    return "unverified"


def definition_lookup() -> dict[str, str]:
    """Every display form of each label, mapped to its definition, for
    the pills' tooltips: passive ("Overruled by"), active ("Overrules"),
    past tense ("Overruled") and both recognized forms ("Overruled as
    recognized by", "Recognizes to be overruled"). Labels in NO_TOOLTIP
    are left out in every form."""
    lookup: dict[str, str] = {}
    for label, text in DEFINITIONS.items():
        if label in NO_TOOLTIP:
            continue
        lookup[label] = text
        lookup[to_active_voice(label)] = text
        lookup[past_tense(label)] = text
        recognized = recognized_definition(text)
        lookup[recognized_form(label)] = recognized
        lookup[recognizes_label(label)] = recognized
    return lookup


def treatment_table() -> list[dict[str, Any]]:
    """The taxonomy by tier for the About page: each tier's direct-history
    labels and its citing-reference labels."""
    rows = []
    for tier in SEVERITY_ORDER:
        labels = [t for t, s in SEVERITY_BY_TREATMENT.items() if s == tier]
        rows.append(
            {
                "severity": tier,
                "direct_history": [
                    t for t in labels if t in DIRECT_HISTORY_TREATMENTS
                ],
                "citing_reference": [
                    t for t in labels if t not in DIRECT_HISTORY_TREATMENTS
                ],
            }
        )
    return rows
