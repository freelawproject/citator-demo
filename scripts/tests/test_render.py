from __future__ import annotations

from render import (
    balance_inline,
    excerpt_from_text,
    render_body_html,
    section_anchor,
)

LONG = "x" * 130


def test_balance_inline_closes_and_drops_strays() -> None:
    assert balance_inline("<em>open") == "<em>open</em>"
    assert balance_inline("stray</em> text") == "stray text"
    assert balance_inline("<em><a>x</em></a>") == "<em><a>x</a></em>"
    assert balance_inline("<p>block</p>") == "<p>block</p>"


def test_excerpt_skips_short_and_counsel_paragraphs() -> None:
    doc = [
        {
            "blocks": [
                {"type": "author", "html": "Chief Justice Roberts"},
                {"type": "paragraph", "html": "Short."},
                {
                    "type": "paragraph",
                    "html": "Smith LLP, 55 Challenger Road, Suite 1. "
                    "Attorneys for Plaintiffs. " + LONG,
                },
                {"type": "paragraph", "html": "The substantive one. " + LONG},
            ],
            "footnotes": [],
        }
    ]
    assert excerpt_from_text(doc).startswith("The substantive one.")
    assert (
        excerpt_from_text("## I\n\nOnly a short one.") == "Only a short one."
    )
    assert excerpt_from_text("") == ""


def test_excerpt_truncates_on_a_sentence() -> None:
    text = ("A sentence that goes on for a while. " * 10).strip()
    out = excerpt_from_text(text, max_chars=100)
    assert out.endswith(".") and len(out) <= 100


def test_section_anchor() -> None:
    assert section_anchor("Opinion of the Court (Roberts)") == (
        "section-Opinion-of-the-Court-Roberts"
    )
    assert section_anchor("") == ""


def test_render_pseudo_markdown_links_scoped_cases() -> None:
    text = (
        '## I\n\nSee <citedCase data-cluster-id="5">A v. B</citedCase> & '
        '<citedCase data-cluster-id="7">C v. D</citedCase>.'
    )
    html, sections = render_body_html(text, frozenset({5}))
    assert sections == [{"id": "I", "title": "I", "anchor": "section-I"}]
    assert '<a class="cited-case" href="/opinion/5/"' in html
    assert "cited-case__severity" not in html
    assert "&amp;" in html


def test_render_writings_with_groups_links_rows_and_footnotes() -> None:
    doc = [
        {
            "title": "Opinion of the Court",
            "blocks": [
                {
                    "type": "paragraph",
                    "html": 'See <citedCase data-group="3" data-case="A v. B">1 U.S. 2'
                    '</citedCase><sup class="fnref" id="fnref-1-1">'
                    '<a href="#fn-1-1">1</a></sup> and <citedCase data-group="3">'
                    "A</citedCase>.",
                }
            ],
            "footnotes": [
                {
                    "label": "1",
                    "html": "Note.",
                    "id": "fn-1-1",
                    "ref_id": "fnref-1-1",
                }
            ],
        }
    ]
    info = {
        3: {
            "name": "A v. B",
            "treatment": "Distinguished by",
            "cited_cluster_id": 9,
            "overall_severity": "Stop",
            "page_url": "/opinion/9/",
        }
    }
    html, sections = render_body_html(doc, frozenset({9}), info)
    assert sections[0]["anchor"] == "section-Opinion-of-the-Court"
    assert html.count('href="#authority-3"') == 2
    # a group with no row renders as plain text, not a link
    plain, _ = render_body_html(doc, frozenset({9}), {})
    assert 'href="#authority-3"' not in plain
    assert '<span class="cited-case">' in plain
    assert html.count("cited-case__severity--stop") == 2
    assert 'data-url="/opinion/9/"' in html
    assert "Distinguishing" in html
    assert '<aside class="opinion-footnotes"' in html
    assert 'href="#fnref-1-1"' in html
