"""The treatment taxonomy: labels, severity tiers, directions and the
wording each side of a treatment uses.

A treatment label is written from the cited case's side ("Distinguished
by"). The Authorities tab, the disposition and the History tab's cards
speak from the acting opinion's side, so labels are rewritten to the
active voice there ("Distinguishing"). A treatment the
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
    "Affirmed by": "Neutral",
}

# most serious first
SEVERITY_ORDER: tuple[str, ...] = (
    "Stop",
    "Warning",
    "Caution",
    "Neutral",
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

# What the acting opinion does, as the Authorities tab, the disposition
# and the History tab's cards show it.
ACTIVE_VOICE: dict[str, str] = {
    "Reversed by": "Reversing",
    "Reversed and remanded by": "Reversing and remanding",
    "Vacated by": "Vacating",
    "Vacated and remanded by": "Vacating and remanding",
    "Overruled by": "Overruling",
    "Abrogated by": "Abrogating",
    "Questioned by": "Questioning",
    "Affirmed in part; Reversed in part by": (
        "Affirming in part; Reversing in part"
    ),
    "Affirmed in part; Vacated in part by": (
        "Affirming in part; Vacating in part"
    ),
    "Disapproved by": "Disapproving",
    "Limited by": "Limiting",
    "Remanded by": "Remanding",
    "Cert. granted by": "Granting cert.",
    "Criticized by": "Criticizing",
    "Distinguished by": "Distinguishing",
    "Declined to follow by": "Declining to follow",
    "Dismissed by": "Dismissing",
    "Affirmed by": "Affirming",
    "Cert. denied by": "Denying cert.",
    "Cited by": "Citing",
}

RECOGNIZED_SUFFIX = " as recognized by"

# What each treatment means, shown when a pill is hovered or focused.
# Each is written once, with {actor} for the opinion applying the
# treatment and {target} for the one receiving it; `definition_lookup`
# fills the two from the reader's side, so the opinion on the page is
# always "this case" (see the fillers above that function).
DEFINITIONS: dict[str, str] = {
    # Direct History
    "Reversed by": "On direct appeal, {actor} reversed {target}.",
    "Reversed and remanded by": (
        "On direct appeal, {actor} reversed {target} and sent the case "
        "back for further proceedings."
    ),
    "Vacated and remanded by": (
        "On direct appeal, {actor} set aside {target}, leaving it without "
        "legal effect, and sent the case back for further proceedings."
    ),
    "Vacated by": (
        "On direct appeal, {actor} set aside {target}, leaving it without "
        "legal effect."
    ),
    "Affirmed in part; Reversed in part by": (
        "On direct appeal, {actor} affirmed part of {target} and reversed "
        "other parts of it."
    ),
    "Affirmed in part; Vacated in part by": (
        "On direct appeal, {actor} affirmed part of {target} and set aside "
        "other parts of it."
    ),
    "Remanded by": (
        "On direct appeal, {actor} sent {target} back for further proceedings."
    ),
    "Cert. granted by": (
        "On a petition for review, {actor} agreed to hear an appeal of "
        "{target}."
    ),
    "Dismissed by": (
        "On direct appeal, {actor} ended the appeal of {target} without "
        "deciding its merits."
    ),
    "Affirmed by": "On direct appeal, {actor} affirmed {target}.",
    "Cert. denied by": (
        "On a petition for review, {actor} refused to hear an appeal of "
        "{target}."
    ),
    # Citing Reference
    "Overruled by": "{actor} expressly overruled all or part of {target}.",
    "Abrogated by": (
        "{actor} effectively, but not explicitly, overruled all or part of "
        "{target}."
    ),
    "Questioned by": (
        "{actor} questioned the continuing validity or precedential value "
        "of {target}, either because another decision implicitly "
        "undermines it or because of intervening events such as judicial "
        "or legislative overruling."
    ),
    "Disapproved by": (
        "{actor} expressly or implicitly disapproved all or part of "
        "{target} for its reasoning or result and reached a contrary "
        "holding, but did not overrule it."
    ),
    "Limited by": (
        "{actor} narrowed the scope or applicability of {target} rather "
        "than extending it or accepting it as authoritative."
    ),
    "Criticized by": (
        "{actor} criticized all or part of the reasoning of {target} but, "
        "unlike Disapproved, did not reach a contrary holding, or the "
        "criticism is dicta."
    ),
    "Distinguished by": (
        "{actor} reached a different result because its facts, procedural "
        "posture or law differ from those of {target}. Sometimes also "
        "called declined to extend."
    ),
    "Declined to follow by": (
        "{actor} chose not to apply the reasoning or ruling of {target}, "
        "and no more specific treatment applies."
    ),
    "Cited by": (
        "{actor} cited, referenced, discussed, interpreted, clarified or "
        "explained {target} without treating it negatively."
    ),
}

# A plain citation: its pill shows no definition and its row no
# evidence card. Every other treatment shows both.
PLAIN_CITATION = "Cited by"
NO_TOOLTIP = frozenset({PLAIN_CITATION})


def has_evidence(treatment: str) -> bool:
    """Whether a treatment's rationale and quote are presented, in either
    form: every treatment but a plain citation. The Authorities and Cited
    By tabs share this rule."""
    return base_treatment(treatment) != PLAIN_CITATION


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
    """What the acting opinion does: "Distinguished by" → "Distinguishing",
    "Overruled as recognized by" → "Recognizing as overruled"."""
    if treatment in ACTIVE_VOICE:
        return ACTIVE_VOICE[treatment]
    if is_recognized(treatment):
        return f"Recognizing as {past_tense(treatment).lower()}"
    return treatment.removesuffix(" by")


def recognizes_label(treatment: str) -> str:
    """Pill text for a treatment this opinion reports another court
    applied: "Recognizing to be overruled"."""
    return f"Recognizing to be {past_tense(treatment).lower()}"


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


# The definitions speak from the reader's side: the opinion on the page
# is "this case" whichever role it plays, and the other party is named by
# what it is to this case.
THIS_CASE = "this case"
CITED_CASE = "the cited case"
# the other party when this case received the treatment
ACTOR_ON_THIS_CASE = {"direct": "another court", "citing": "a later case"}
# the other party when this case applied the treatment
TARGET_OF_THIS_CASE = {"direct": "the decision below", "citing": CITED_CASE}
# the court whose act is only reported, by this case or by a later one
REPORTED_ACTOR = {"direct": "another court", "citing": "another case"}


def _kind(label: str) -> str:
    return "direct" if label in DIRECT_HISTORY_TREATMENTS else "citing"


def _definition(label: str, actor: str, target: str) -> str:
    text = DEFINITIONS[label].format(actor=actor, target=target)
    return text[:1].upper() + text[1:]


def _reported(reporter: str, text: str) -> str:
    """ "Another court reversed this case." → "A later case noted that
    another court reversed this case."."""
    return f"{reporter} noted that {text[:1].lower()}{text[1:]}"


def definition_lookup() -> dict[str, str]:
    """Every display form of each label, mapped to its definition from
    the reader's side, for the pills' tooltips. The passive ("Overruled
    by") and past-tense ("Overruled") forms are shown where this case
    received the treatment; the active form ("Overruling") where it
    applied it; "Overruled as recognized by" where a later case reports
    the treatment of this case, and "Recognizing to be overruled" where
    this case reports the treatment of a cited case. Labels in
    NO_TOOLTIP are left out in every form."""
    lookup: dict[str, str] = {}
    for label in DEFINITIONS:
        if label in NO_TOOLTIP:
            continue
        kind = _kind(label)
        received = _definition(label, ACTOR_ON_THIS_CASE[kind], THIS_CASE)
        lookup[label] = received
        lookup[past_tense(label)] = received
        lookup[to_active_voice(label)] = _definition(
            label, THIS_CASE, TARGET_OF_THIS_CASE[kind]
        )
        lookup[recognized_form(label)] = _reported(
            "A later case",
            _definition(label, REPORTED_ACTOR[kind], THIS_CASE),
        )
        lookup[recognizes_label(label)] = _reported(
            "This case", _definition(label, REPORTED_ACTOR[kind], CITED_CASE)
        )
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
