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
        ("Affirmed by", "Positive"),
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
    assert to_active_voice("Distinguished by") == "Distinguishes"
    assert (
        to_active_voice("Affirmed in part; Reversed in part by")
        == "Affirms in part; Reverses in part"
    )
    assert (
        to_active_voice("Overruled as recognized by")
        == "Recognizes as overruled"
    )
    assert to_active_voice("Unknown by") == "Unknown"
    assert recognizes_label("Overruled by") == "Recognizes to be overruled"
    assert recognizes_label("Cert. granted as recognized by") == (
        "Recognizes to be cert. granted"
    )


def test_worst_tier() -> None:
    assert worst_tier(["Neutral", "Stop", "Caution"]) == "Stop"
    assert worst_tier(["Positive", "Neutral"]) == "Neutral"
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


def test_definition_lookup_covers_every_pill_form() -> None:
    lookup = definition_lookup()
    overruled = DEFINITIONS["Overruled by"]
    assert lookup["Overruled by"] == overruled
    assert lookup["Overrules"] == overruled
    assert lookup["Overruled"] == overruled
    recognized = (
        "The citing case notes that the acting case expressly overrules "
        "all or part of the target case."
    )
    assert lookup["Overruled as recognized by"] == recognized
    assert lookup["Recognizes to be overruled"] == recognized
    assert lookup["Reversed as recognized by"].startswith(
        "The citing case notes that on direct appeal, the acting case"
    )
    for plain in ("Cited by", "Cites", "Cited", "Cited as recognized by"):
        assert plain not in lookup
    assert lookup["Granted cert."] == DEFINITIONS["Cert. granted by"]
    assert "Ordered" not in lookup


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
        "Positive",
    ]
    positive = next(r for r in rows if r["severity"] == "Positive")
    assert positive["direct_history"] == ["Affirmed by"]
