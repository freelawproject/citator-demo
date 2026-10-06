from __future__ import annotations

import pytest

from taxonomy import (
    DEFINITIONS,
    SEVERITY_BY_TREATMENT,
    definition_lookup,
    direction_for,
    recognizes_label,
    row_validation,
    severity_for,
    to_active_voice,
    treatment_table,
    validate_pills,
    worst_tier,
)


@pytest.mark.parametrize(
    ("treatment", "severity"),
    [
        ("Overruled by", "Stop"),
        ("Overruled as recognized by", "Stop"),
        ("Limited by", "Warning"),
        ("Distinguished by", "Caution"),
        ("Cited by", "Neutral"),
        ("Affirmed by", "Neutral"),
        ("Something else", "Other"),
        (None, "Other"),
    ],
)
def test_severity_for(treatment: str | None, severity: str) -> None:
    assert severity_for(treatment) == severity


@pytest.mark.parametrize(
    ("treatment", "direction"),
    [
        ("Reversed by", "Direct History"),
        ("Cert. denied by", "Direct History"),
        ("Distinguished by", "Citing Reference"),
        ("Overruled as recognized by", "Related Reference"),
    ],
)
def test_direction_for(treatment: str, direction: str) -> None:
    assert direction_for(treatment) == direction


def test_active_voice_and_recognized_wording() -> None:
    assert to_active_voice("Distinguished by") == "Distinguishing"
    assert (
        to_active_voice("Affirmed in part; Reversed in part by")
        == "Affirming in part; Reversing in part"
    )
    assert to_active_voice("Cert. denied by") == "Denying cert."
    assert (
        to_active_voice("Overruled as recognized by")
        == "Recognizing as overruled"
    )
    assert to_active_voice("Unknown by") == "Unknown"
    assert recognizes_label("Overruled by") == "Recognizing to be overruled"
    assert recognizes_label("Cert. granted as recognized by") == (
        "Recognizing to be cert. granted"
    )


def test_worst_tier() -> None:
    assert worst_tier(["Neutral", "Stop", "Caution"]) == "Stop"
    assert worst_tier(["Neutral", "Caution"]) == "Caution"
    assert worst_tier([None, "Caution"]) == "Caution"
    assert worst_tier([], default="none") == "none"


def pills(*specs: tuple[str, str]) -> list[dict[str, str]]:
    return [
        {"kind": kind, "treatment": t, "severity": severity_for(t)}
        for kind, t in specs
    ]


def test_validate_pills_unreviewed_is_unverified() -> None:
    assert validate_pills(pills(("applied", "Distinguished by")), "") == [
        "unverified"
    ]


def test_validate_pills_agreement_marks_only_the_matching_pill() -> None:
    states = validate_pills(
        pills(("applied", "Cited by"), ("recognized", "Overruled by")),
        "Overruled as recognized by",
    )
    assert states == ["unverified", "agree"]


def test_validate_pills_neutral_expert_never_disagrees() -> None:
    states = validate_pills(pills(("applied", "Limited by")), "Cited by")
    assert states == ["unverified"]


def test_validate_pills_missed_negative_marks_the_applied_pill() -> None:
    states = validate_pills(
        pills(("applied", "Cited by"), ("recognized", "Affirmed by")),
        "Overruled by",
    )
    assert states == ["disagree", "unverified"]


def test_validate_pills_distinguished_read_as_cited_is_a_close_call() -> None:
    assert validate_pills(
        pills(("applied", "Cited by")), "Distinguished by"
    ) == ["unverified"]
    assert validate_pills(
        pills(("applied", "Limited by")), "Distinguished by"
    ) == ["unverified"]
    assert validate_pills(
        pills(("applied", "Criticized by")), "Distinguished by"
    ) == ["disagree"]


def test_row_validation_precedence() -> None:
    assert row_validation(["unverified", "disagree", "agree"]) == "disagree"
    assert row_validation(["unverified", "agree"]) == "agree"
    assert row_validation(["unverified"]) == "unverified"


def test_every_treatment_has_a_definition() -> None:
    assert sorted(DEFINITIONS) == sorted(SEVERITY_BY_TREATMENT)


def test_definition_lookup_speaks_from_the_page() -> None:
    lookup = definition_lookup()
    # this case received the treatment: passive and past-tense forms
    received = "A later case expressly overruled all or part of this case."
    assert lookup["Overruled by"] == received
    assert lookup["Overruled"] == received
    # this case applied it: the active form
    assert lookup["Overruling"] == (
        "This case expressly overruled all or part of the cited case."
    )
    # a later case reports the treatment of this case
    assert lookup["Overruled as recognized by"] == (
        "A later case noted that another case expressly overruled all or "
        "part of this case."
    )
    # this case reports the treatment of a cited case
    assert lookup["Recognizing to be overruled"] == (
        "This case noted that another case expressly overruled all or "
        "part of the cited case."
    )
    # direct history names a court, and the decision below on the acting side
    assert lookup["Reversed and remanded by"] == (
        "On direct appeal, another court reversed this case and sent the "
        "case back for further proceedings."
    )
    assert lookup["Reversing and remanding"] == (
        "On direct appeal, this case reversed the decision below and sent "
        "the case back for further proceedings."
    )
    assert lookup["Reversed as recognized by"].startswith(
        "A later case noted that on direct appeal, another court reversed "
        "this case."
    )
    assert lookup["Recognizing to be reversed"] == (
        "This case noted that on direct appeal, another court reversed "
        "the cited case."
    )
    for plain in ("Cited by", "Citing", "Cited", "Cited as recognized by"):
        assert plain not in lookup
    assert "acting case" not in " ".join(lookup.values())
    assert "Ordered" not in lookup


def test_every_definition_fills_both_blanks() -> None:
    lookup = definition_lookup()
    assert all("{" not in text for text in lookup.values())
    assert all(text[0].isupper() for text in lookup.values())


def test_treatment_table_covers_every_label_once() -> None:
    rows = treatment_table()
    listed = [
        t
        for row in rows
        for t in row["direct_history"] + row["citing_reference"]
    ]
    assert sorted(listed) == sorted(SEVERITY_BY_TREATMENT)
    assert [r["severity"] for r in rows] == [
        "Stop",
        "Warning",
        "Caution",
        "Neutral",
    ]
    neutral = next(r for r in rows if r["severity"] == "Neutral")
    assert "Affirmed by" in neutral["direct_history"]
