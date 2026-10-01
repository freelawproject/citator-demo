from __future__ import annotations

import pytest

from cl_html import (
    citation_map,
    cluster_to_document_text,
    inject_citations,
    looks_like_heading,
    pre_html_to_blocks,
    structured_html_to_blocks,
)

CL_LINK = (
    '<span class="citation" data-id="9"><a href="/opinion/145843/gall/" '
    'aria-description="Citation for case: Gall v. United States">'
    "552 U.S. 38</a></span>"
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("II", True),
        ("A", True),
        ("II. ANALYSIS", True),
        ("a. Diminution in value", True),
        ("BACKGROUND", True),
        ("14. An officer's personal knowledge of the facts", False),
        ("It is so ordered.", False),
        ("Judge Davila noted:", False),
        ("", False),
    ],
)
def test_looks_like_heading(text: str, expected: bool) -> None:
    assert looks_like_heading(text) is expected


def test_structured_html_blocks_types_and_citations() -> None:
    html = (
        '<opinion type="majority"><author>Justice Roberts</author>'
        "<p>delivered the opinion of the Court.</p>"
        f"<p>We follow {CL_LINK}, as before.<footnotemark>1</footnotemark></p>"
        "<p>II. ANALYSIS</p><blockquote>Quoted text.</blockquote>"
        '<footnote label="1">The note.</footnote></opinion>'
    )
    blocks, footnotes, opinion_type = structured_html_to_blocks(html)
    assert opinion_type == "majority"
    assert [b["type"] for b in blocks] == [
        "author",
        "paragraph",
        "heading",
        "blockquote",
    ]
    # a lower-case continuation is merged into the author line
    assert (
        blocks[0]["html"]
        == "Justice Roberts delivered the opinion of the Court."
    )
    assert '<citedCase data-cluster-id="145843"' in blocks[1]["html"]
    assert 'data-case="Gall v. United States"' in blocks[1]["html"]
    assert footnotes == [{"label": "1", "html": "The note."}]


def test_structured_html_drops_page_furniture_and_unresolved_cites() -> None:
    html = (
        '<opinion><p>Text<span class="star-pagination">*12</span> continues '
        '<span class="citation no-link">12 U.S.C. § 1</span>.</p></opinion>'
    )
    blocks, _, _ = structured_html_to_blocks(html)
    assert blocks == [
        {"type": "paragraph", "html": "Text continues 12 U.S.C. § 1."}
    ]


def test_pre_dump_recovers_paragraphs() -> None:
    html = (
        '<pre class="inline">\n'
        "                    OPINION AND ORDER\n"
        "    The plaintiff moves for summary judgment on the first claim and\n"
        "for costs, and the defendant opposes both of those motions in full.\n"
        "                                   3\n"
        "    The motion is denied.\n"
        "</pre>"
    )
    blocks = pre_html_to_blocks(html)
    assert blocks[0] == {"type": "heading", "html": "OPINION AND ORDER"}
    assert blocks[1]["html"] == (
        "The plaintiff moves for summary judgment on the first claim and "
        "for costs, and the defendant opposes both of those motions in full."
    )
    assert blocks[2]["html"] == "The motion is denied."


def test_citation_map_and_injection() -> None:
    cite_map = citation_map([f"<p>{CL_LINK}</p>"])
    assert cite_map["552 U.S. 38"] == ("145843", "Gall v. United States")
    out = inject_citations("See 552 U.S. 38, 41 and <em>id.</em>", cite_map)
    assert out.startswith('See <citedCase data-cluster-id="145843"')
    assert out.endswith("</citedCase>, 41 and <em>id.</em>")


def test_cluster_titles_only_when_several_writings() -> None:
    one = cluster_to_document_text(
        [{"html": "<p>Only text.</p>", "type": "010combined"}]
    )
    assert one[0]["title"] is None
    two = cluster_to_document_text(
        [
            {"html": "<p>Lead.</p>", "type": "020lead", "author": "Roberts"},
            {
                "html": "<p>Dissent.</p>",
                "type": "040dissent",
                "author": "Scalia",
            },
        ]
    )
    assert [w["title"] for w in two] == [
        "Opinion of the Court (Roberts)",
        "Dissent (Scalia)",
    ]
