"""Render an opinion's document to the page html.

The document is either the structured form `cl_html.cluster_to_document_text`
produces (a list of writings with typed blocks and footnotes) or the
pseudo-markdown string the mock fixtures use (`## Title` section headers,
blank-line paragraphs, inline `<citedCase>` tags). Both render to one html
string plus the section metadata the page's "Jump to" list reads.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from html import escape
from typing import Any

from cl_html import document_plain_paragraphs
from taxonomy import NEGATIVE_TIERS, past_tense, to_active_voice

SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
# <citedCase data-group="N" data-cluster-id="X" data-case="Y" data-manual="1">
# label</citedCase>, every attribute optional (see cl_html.cited_case_tag).
CITED_CASE_RE = re.compile(r"<citedCase([^>]*)>(.+?)</citedCase>")
_ATTR_RE = re.compile(r'([a-z-]+)="([^"]*)"')
# Counsel-appearance paragraphs from a PDF caption: never a useful excerpt.
COUNSEL_BLOCK_RE = re.compile(
    r"\bAttorneys? for\b|\b(?:LLP|LLC|PLLC|P\.\s?C\.)\b.*\b(?:Suite|Street|Avenue|Road)\b",
    re.S,
)
INLINE_TAGS = frozenset(
    {"em", "strong", "i", "b", "sup", "sub", "u", "small", "span", "a"}
)
_TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*?)(/?)>")

# block type → (tag, class)
BLOCK_TAG: dict[str, tuple[str, str]] = {
    "paragraph": ("p", ""),
    "blockquote": ("blockquote", ""),
    "heading": ("h3", "opinion-heading"),
    "author": ("p", "opinion-author"),
    "judges": ("p", "opinion-judges"),
    "attorneys": ("p", "opinion-attorneys"),
}

Document = str | list[dict[str, Any]]
GroupInfo = dict[int, dict[str, Any]]


def excerpt_from_text(
    document_text: Document, max_chars: int = 280, min_chars: int = 120
) -> str:
    """First substantive paragraph, trimmed to a sentence boundary.

    Paragraphs shorter than `min_chars` (author lines, captions) and
    counsel blocks are skipped; the first paragraph is the fallback.
    """
    if isinstance(document_text, str):
        text = SECTION_RE.sub("", document_text)
        text = CITED_CASE_RE.sub(r"\2", text)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    else:
        paragraphs = document_plain_paragraphs(document_text)
    if not paragraphs:
        return ""
    substantive = [
        p
        for p in paragraphs
        if len(p) >= min_chars and not COUNSEL_BLOCK_RE.search(p)
    ]
    first = substantive[0] if substantive else paragraphs[0]
    if len(first) <= max_chars:
        return first
    truncated = first[:max_chars]
    cut = truncated.rfind(". ")
    if cut > max_chars * 0.6:
        return truncated[: cut + 1]
    return truncated.rstrip() + "…"


def section_anchor(section_id: str) -> str:
    """A section title → its element id ("Opinion of the Court" →
    "section-Opinion-of-the-Court")."""
    safe = re.sub(r"[^A-Za-z0-9]+", "-", section_id).strip("-")
    return f"section-{safe}" if safe else ""


def balance_inline(html: str) -> str:
    """Close inline tags a block leaves open and drop closers with no
    opener, so emphasis that runs across a paragraph break in the source
    does not re-open inside every later block."""
    out: list[str] = []
    stack: list[str] = []
    pos = 0
    for m in _TAG_RE.finditer(html):
        tag = m.group(2).lower()
        out.append(html[pos : m.start()])
        pos = m.end()
        if tag not in INLINE_TAGS or m.group(4):
            out.append(m.group(0))
            continue
        if not m.group(1):
            stack.append(tag)
            out.append(m.group(0))
        elif stack and stack[-1] == tag:
            stack.pop()
            out.append(m.group(0))
        elif tag in stack:
            # interleaved (<em><a></em></a>): close the inner tags first
            while stack[-1] != tag:
                out.append(f"</{stack.pop()}>")
            stack.pop()
            out.append(m.group(0))
    out.append(html[pos:])
    out.extend(f"</{tag}>" for tag in reversed(stack))
    return "".join(out)


def _cited_case_attrs(attr_text: str) -> dict[str, str]:
    return dict(_ATTR_RE.findall(attr_text))


def _group_title(name: str, info: dict[str, Any]) -> str:
    """Hover text for a citation: the authority's name, what this opinion
    does to it and what it recognizes. "&#10;" is a newline in a title."""
    lines = [escape(name)] if name else []
    lines.append(to_active_voice(info.get("treatment") or "Cited by"))
    recognized = [
        past_tense(x["treatment"])
        for x in info.get("recognized") or []
        if x.get("treatment")
    ]
    if recognized:
        lines.append("Recognizes: " + ", ".join(escape(r) for r in recognized))
    return "&#10;".join(lines)


class CitationLinker:
    """Turns `<citedCase>` tags into the page's citation markup: a chip
    plus a small marker coloured by the severity of the case's treatment.

    With `group_info` (authority number → the Authorities-tab row, with
    `overall_severity`, `name` and `page_url`) every citation links to
    its row (`#authority-N`) and carries the data the occurrence navigator
    shows. Without it, scoped clusters link to their page and the marker
    is neutral.
    """

    def __init__(
        self, scoped_ids: frozenset[int], group_info: GroupInfo | None = None
    ) -> None:
        self.scoped_ids = scoped_ids
        self.group_info = group_info

    def link(self, inline_html: str) -> str:
        """Replace every `<citedCase>` tag in already-escaped html."""
        return CITED_CASE_RE.sub(self._replace, inline_html)

    def _replace(self, m: re.Match[str]) -> str:
        attrs = _cited_case_attrs(m.group(1))
        label = m.group(2)
        case_name = attrs.get("data-case", "")
        cluster_id = (
            int(attrs["data-cluster-id"])
            if attrs.get("data-cluster-id")
            else None
        )
        if self.group_info is not None and attrs.get("data-group"):
            return self._grouped(
                int(attrs["data-group"]),
                label,
                case_name,
                cluster_id,
                bool(attrs.get("data-manual")),
            )
        if cluster_id is None:
            return label
        return self._plain(cluster_id, label, case_name)

    def _grouped(
        self,
        n: int,
        label: str,
        case_name: str,
        cluster_id: int | None,
        manual: bool,
    ) -> str:
        info = (self.group_info or {}).get(n)
        if info is None:
            # no Authorities row for this group (the opinion citing itself)
            return f'<span class="cited-case">{label}</span>'
        name = info.get("name") or case_name
        classes = "cited-case"
        if manual:
            classes += " cited-case--added"
        return (
            f'<a class="cited-case-wrap" href="#authority-{n}" '
            f'title="{_group_title(name, info)}" data-group="{n}" '
            f'data-name="{escape(name)}" '
            f'data-url="{escape(info.get("page_url") or "")}">'
            f'<span class="{classes}">{label}</span>'
            f"{_severity_marker(info.get('overall_severity'))}</a>"
        )

    def _plain(self, cluster_id: int, label: str, case_name: str) -> str:
        """A citation with no treatment data, linked to the case's page
        when the site has it."""
        title = f' title="{escape(case_name)}"' if case_name else ""
        if cluster_id in self.scoped_ids:
            cite = (
                f'<a class="cited-case" href="/opinion/{cluster_id}/"{title}>'
                f"{label}</a>"
            )
        else:
            cite = f'<span class="cited-case"{title}>{label}</span>'
        return f'<span class="cited-case-wrap">{cite}{_severity_marker(None)}</span>'


def _severity_marker(severity: str | None) -> str:
    """The small coloured marker after a citation: the most serious
    treatment on the case's Authorities row. Nothing for a case with no
    negative treatment."""
    if not severity or severity not in NEGATIVE_TIERS:
        return ""
    tier = severity.lower()
    return (
        f'<span class="cited-case__severity cited-case__severity--{tier}" '
        f'role="img" aria-label="Treatment severity: {tier}"></span>'
    )


def render_body_html(
    document_text: Document,
    scoped_ids: frozenset[int],
    group_info: GroupInfo | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """Render a document to (body html, section metadata). Each section
    is {id, title, anchor}; the page's "Jump to" list is built from it."""
    linker = CitationLinker(scoped_ids, group_info)
    if not isinstance(document_text, str):
        return _render_writings(document_text, linker)
    return _render_pseudo_markdown(document_text, linker)


def _render_writings(
    writings: list[dict[str, Any]], linker: CitationLinker
) -> tuple[str, list[dict[str, str]]]:
    """One <section> per writing, with a heading when the writing has a
    title, typed blocks, and footnotes as an ordered list whose in-text
    marks link down and whose labels link back."""
    sections: list[dict[str, str]] = []
    chunks: list[str] = []
    for w, writing in enumerate(writings, start=1):
        title = writing.get("title")
        anchor = section_anchor(title) if title else f"writing-{w}"
        parts: list[str] = []
        if title:
            sections.append({"id": title, "title": title, "anchor": anchor})
            parts.append(f"<h2>{escape(title)}</h2>")
        for block in writing["blocks"]:
            tag, cls = BLOCK_TAG.get(block["type"], ("p", ""))
            cls_attr = f' class="{cls}"' if cls else ""
            inner = balance_inline(linker.link(block["html"]))
            parts.append(f"<{tag}{cls_attr}>{inner}</{tag}>")
        if writing.get("footnotes"):
            parts.append(_render_footnotes(writing["footnotes"], linker.link))
        data_id = escape(title) if title else f"writing-{w}"
        chunks.append(
            f'<section id="{anchor}" data-section-id="{data_id}">'
            f"{''.join(parts)}</section>"
        )
    return "\n".join(chunks), sections


def _render_footnotes(
    footnotes: list[dict[str, Any]], link: Callable[[str], str]
) -> str:
    items = []
    for fn in footnotes:
        label = escape(fn["label"])
        items.append(
            f'<li id="{fn["id"]}"><span class="fn-label">'
            f'<a class="fn-label__link" href="#{fn["ref_id"]}" '
            f'aria-label="Back to reference {label}">{label}</a></span>'
            f'<div class="fn-body"><p>{balance_inline(link(fn["html"]))}'
            f"</p></div></li>"
        )
    return (
        '<aside class="opinion-footnotes" aria-label="Footnotes">'
        '<h3 class="opinion-heading opinion-heading--notes">Footnotes</h3>'
        f"<ol>{''.join(items)}</ol></aside>"
    )


def _render_pseudo_markdown(
    text: str, linker: CitationLinker
) -> tuple[str, list[dict[str, str]]]:
    """The mock fixtures' format: `## Title` sections of blank-line
    separated paragraphs with inline `<citedCase>` tags."""
    parts = SECTION_RE.split(text.strip())
    preamble = parts[0]
    section_pairs = list(zip(parts[1::2], parts[2::2], strict=False))
    sections = [
        {
            "id": sid.strip(),
            "title": sid.strip(),
            "anchor": section_anchor(sid.strip()),
        }
        for sid, _ in section_pairs
    ]
    chunks: list[str] = []
    if preamble.strip():
        chunks.append(_render_paragraphs(preamble, linker))
    for sid, body in section_pairs:
        sid_clean = sid.strip()
        chunks.append(
            f'<section id="{section_anchor(sid_clean)}" '
            f'data-section-id="{escape(sid_clean)}">'
            f"<h2>{escape(sid_clean)}</h2>"
            f"{_render_paragraphs(body, linker)}</section>"
        )
    return "\n".join(chunks), sections


def _render_paragraphs(text: str, linker: CitationLinker) -> str:
    """Escape the prose, keep the `<citedCase>` tags, then link them."""
    rendered = []
    for paragraph in (p.strip() for p in text.strip().split("\n\n")):
        if not paragraph:
            continue
        out = []
        last = 0
        for m in CITED_CASE_RE.finditer(paragraph):
            out.append(escape(paragraph[last : m.start()]))
            out.append(
                f"<citedCase{m.group(1)}>{escape(m.group(2))}</citedCase>"
            )
            last = m.end()
        out.append(escape(paragraph[last:]))
        rendered.append(f"<p>{linker.link(''.join(out))}</p>")
    return "\n".join(rendered)
