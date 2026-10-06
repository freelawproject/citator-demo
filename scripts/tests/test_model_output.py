from __future__ import annotations

from model_output import (
    act_verbs,
    below_entry,
    canonical_court,
    clean_authority_name,
    disposition_label,
    disposition_treatment,
    document_token_streams,
    expand_quote,
    is_case_group,
    quote_names_case,
    sentence_bounds,
    verify_quote,
)


def test_clean_authority_name() -> None:
    assert (
        clean_authority_name("Troppi v. Scarf (leave denied)")
        == "Troppi v. Scarf"
    )
    assert (
        clean_authority_name("Hauck v. Hauck (Hauck II)")
        == "Hauck v. Hauck (Hauck II)"
    )


def test_is_case_group() -> None:
    assert is_case_group({"name": "Smith v. Jones", "cited_as": ["Id."]})
    assert is_case_group({"name": "", "cited_as": ["447 F. Supp. 3d at 167"]})
    assert is_case_group({"name": "", "citations": ["4 Wheat. 316, 405"]})
    assert is_case_group({"name": "", "cited_as": ["82 F.4th at"]})
    assert is_case_group({"name": "", "cited_as": ["263 F. App’x 286"]})
    assert is_case_group({"name": "", "cited_as": ["591 U. S. ___"]})
    assert is_case_group({"name": "", "cited_as": ["465 U. S., at 788–789"]})
    assert is_case_group({"name": "", "cited_as": ["70 U.S. (3 Wall.) 407"]})
    assert is_case_group({"name": "", "cited_as": ["Bruton"]})
    assert is_case_group({"name": "", "cited_as": ["Sattar II"]})
    assert is_case_group({"name": "", "cited_as": ["In re Google"]})
    assert is_case_group({"name": "", "cited_as": ["NFIB v. OSHA"]})
    assert not is_case_group({"name": "", "cited_as": ["FCC 11-9900"]})
    assert not is_case_group({"name": "", "cited_as": ["See, e.g. id. ¶¶ 40"]})
    assert not is_case_group({"name": "", "cited_as": ["136 FERC ¶ 61,051"]})
    assert not is_case_group({"name": "", "cited_as": ["Public Law 99-240"]})
    assert not is_case_group({"name": "", "cited_as": ["42 U. S. C. § 1304"]})
    assert not is_case_group({"name": "", "cited_as": ["79 Stat. 343"]})
    assert not is_case_group(
        {"name": "", "cited_as": ["14 U. Pa. J. Const. L. 431"]}
    )
    assert not is_case_group(
        {"name": "", "cited_as": ["159 U. Pa. L. Rev. 1825"]}
    )
    assert not is_case_group({"name": "", "cited_as": ["Ibid."]})
    assert not is_case_group({"name": "", "cited_as": ["id.", "Id. at 3"]})


def test_canonical_court() -> None:
    display = {
        "scotus": "Supreme Court of the United States",
        "ca9": "Ninth Circuit",
    }
    assert canonical_court(display, "the United States Supreme Court") == (
        "scotus",
        "Supreme Court of the United States",
    )
    assert canonical_court(display, "the Ninth Circuit") == (
        "ca9",
        "Ninth Circuit",
    )
    assert canonical_court(display, "the  Second Circuit") == (
        "ca2",
        "Court of Appeals for the Second Circuit",
    )
    assert canonical_court(display, "a state court") == ("", "a state court")


def test_act_verbs_normalise_phrasings() -> None:
    assert act_verbs("Affirmed in part; Reversed in part") == {
        "affirmed",
        "reversed",
    }
    assert act_verbs("Reversed and remanded") == {"reversed", "remanded"}
    assert act_verbs("Reversed by") == {"reversed"}


def test_below_entry_prefers_the_matching_name() -> None:
    record = {
        "case_name": "Harper v. Virginia Department of Taxation",
        "on_appeal": [
            {
                "court": "Supreme Court of Virginia",
                "name": "Lewy v. Commonwealth",
            },
            {
                "court": "Supreme Court of Virginia",
                "name": "Harper v. Commonwealth",
            },
        ],
    }
    entry = below_entry(record)
    assert entry is not None and entry["name"] == "Harper v. Commonwealth"
    assert below_entry({"case_name": "X", "on_appeal": []}) is None
    assert below_entry(
        {"case_name": "X", "on_appeal": [{"court": "A court"}]}
    ) == {"court": "A court"}


def test_disposition_forms() -> None:
    assert disposition_label(None) is None
    assert disposition_label(
        {"label": "Reversed and remanded", "text": "x"}
    ) == {
        "label": "Reversing and remanding",
        "severity": "Stop",
        "text": "",
    }
    assert disposition_label(
        {"label": "Other", "text": "Motion granted."}
    ) == {
        "label": "Ordered",
        "severity": "Neutral",
        "text": "Motion granted.",
    }
    assert disposition_label({"label": "None", "text": ""}) is None


def test_disposition_treatment_matches_the_status_row() -> None:
    assert disposition_treatment({"label": "Affirmed", "text": ""}) == {
        "treatment": "Affirmed by",
        "severity": "Neutral",
        "text": "",
    }
    assert disposition_treatment({"label": "Other", "text": "Denied."}) == {
        "treatment": "Ordered by",
        "severity": "Neutral",
        "text": "Denied.",
    }
    assert disposition_treatment({"label": "Modified", "text": ""}) == {
        "treatment": "Ordered by",
        "severity": "Neutral",
        "text": "Modified",
    }
    assert disposition_treatment({"label": "None", "text": ""}) is None
    assert disposition_treatment(None) is None


def test_sentence_bounds_respects_legal_abbreviations() -> None:
    text = "See Smith v. Jones, 1 U.S. 2 (1990). The court agreed. Next."
    start = text.index("The court")
    assert (
        text[slice(*sentence_bounds(text, start, start + 3))].strip()
        == "The court agreed."
    )
    start = text.index("Smith")
    assert text[slice(*sentence_bounds(text, start, start + 5))] == (
        "See Smith v. Jones, 1 U.S. 2 (1990)."
    )


DOCUMENT = [
    {
        "title": None,
        "blocks": [
            {
                "type": "paragraph",
                "html": "The “clearly established” standard applies here. "
                "We therefore reverse the judgment below. The officers acted "
                "reasonably under the circumstances they faced.",
            },
            {
                "type": "paragraph",
                "html": " ".join(
                    ["Filler words between the two passages."] * 12
                ),
            },
            {
                "type": "paragraph",
                "html": "The court remanded for further proceedings consistent "
                "with this opinion.",
            },
        ],
        "footnotes": [],
    }
]


def test_expand_quote_widens_to_the_sentence() -> None:
    assert expand_quote(DOCUMENT, "we therefore reverse") == (
        "We therefore reverse the judgment below."
    )
    assert (
        expand_quote(DOCUMENT, "not in the text at all")
        == "not in the text at all"
    )
    # straight quotes in the model's words match curly ones in the text
    assert expand_quote(DOCUMENT, '"clearly established" standard') == (
        "The “clearly established” standard applies here."
    )


def test_verify_quote_statuses() -> None:
    streams = document_token_streams(DOCUMENT)
    assert (
        verify_quote(streams, "We therefore reverse the judgment below.")[
            "status"
        ]
        == "found"
    )
    stitched = (
        "We therefore reverse the judgment below. … The court remanded for "
        "further proceedings consistent with this opinion."
    )
    assert verify_quote(streams, stitched)["status"] == "stitched"
    partial = (
        "The clearly established standard applies here … "
        "The officers acted with malice and in bad faith throughout."
    )
    assert verify_quote(streams, partial)["status"] == "partial"
    assert (
        verify_quote(streams, "entirely different words that never appear")[
            "status"
        ]
        == "missing"
    )
    assert verify_quote(streams, "too short")["status"] == "short"


def test_quote_names_case() -> None:
    assert (
        quote_names_case("See 552 U.S. 38, 41.", ["552 U.S. 38"], "Gall v. US")
        == "cite"
    )
    assert (
        quote_names_case("As Gall explained,", [], "Gall v. United States")
        == ""
    )
    assert (
        quote_names_case("As Pearson explained,", [], "Pearson v. Callahan")
        == "name"
    )
