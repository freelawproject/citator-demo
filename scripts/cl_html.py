"""Convert CourtListener (or Centralia) opinion HTML into the demo's
structured document format.

The output of `cluster_to_document_text` is a list of WRITINGS:

    [{"title": "Opinion of the Court (Roberts)" | None,
      "blocks": [{"type": ..., "html": ...}, ...],
      "footnotes": [{"label": "1", "html": ...}, ...]}, ...]

Block types: author, judges, heading, paragraph, blockquote. `html` is
SANITISED inline html: escaped text plus <em>, <strong>,
<citedCase data-cluster-id="N">…</citedCase> for resolved case citations and
<sup class="fnref" id="fnref-W-N"><a href="#fn-W-N">N</a></sup> footnote
marks (W = writing index, so ids stay unique across a cluster's writings).
render.render_body_html turns this into the page html; it still accepts the
older plain-string pseudo-markdown that mock_data uses. Working with the
citator's own output (quotes, treatments, dispositions) lives in
model_output.

Three source flavours are handled:

1. Structured CourtListener html (`<opinion>` root, Harvard / Lawbox /
   Columbia sources): <p>, <blockquote>, <author>, <judges>; footnotes in
   <footnote label="n"> or <div class="footnote">; marks in <footnotemark>
   or <a class="footnote">; page markers (<page-number>, .star-pagination,
   a.page-label) dropped. Headings are NOT tagged in this html — a <p> is
   promoted to a heading when it looks like one (short enumerated or
   all-caps line, or a paragraph that is entirely <strong>).
2. `<pre class="inline">` dumps (RECAP / scraped PDFs through pdftotext): no
   markup, so paragraphs are recovered from the layout — blank lines,
   first-line indents and centred headings start a paragraph, hard-wrapped
   lines are joined, bare page numbers and CM/ECF stamps dropped.
3. Centralia's ingest html (`<div class="opinion">`): div.byline → author,
   h3.bhead → heading, div.pgbreak dropped, sup.fnmark marks, div.fns /
   div.fn footnotes. Centralia resolves no citations, so `citation_map` +
   `inject_citations` carry CourtListener's resolved reporter cites over
   by exact string match.

A resolved CourtListener citation
    <span class="citation" data-id="X"><a href="/opinion/N/slug/#page">text</a></span>
becomes <citedCase data-cluster-id="N">text</citedCase> — the cluster id is
the number in the href path, NOT data-id. Unresolved (`no-link`) and
ambiguous (`multiple-matches`) citations stay plain text.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from html.parser import HTMLParser
from typing import Any

CITED_CASE_HREF_RE = re.compile(r"^/opinion/(\d+)/")

# Writing labels: the <opinion type="..."> attribute is more specific than
# CourtListener's Opinion.type code, so it wins when present.
OPINION_TAG_LABEL = {
    "majority": "Opinion of the Court",
    "plurality": "Plurality opinion",
    "concurrence": "Concurrence",
    "concurring-in-part-and-dissenting-in-part": (
        "Concurring in part and dissenting in part"
    ),
    "dissent": "Dissent",
    "per-curiam": "Per curiam",
    "combined": "Opinion",
}
CL_TYPE_LABEL = {
    "010combined": "Opinion",
    "015unamimous": "Unanimous opinion",
    "020lead": "Opinion of the Court",
    "025plurality": "Plurality opinion",
    "030concurrence": "Concurrence",
    "035concurrenceinpart": "Concurring in part",
    "040dissent": "Dissent",
    "050addendum": "Addendum",
    "060remittitur": "Remittitur",
    "070rehearing": "On rehearing",
    "080onthemerits": "On the merits",
    "090onmotiontostrike": "On motion to strike",
    "100trialcourt": "Trial court order",
}

# Block-level tags and the block type each produces.
BLOCK_TYPE = {
    "p": "paragraph",
    "li": "paragraph",
    "center": "paragraph",
    "blockquote": "blockquote",
    "author": "author",
    "judges": "judges",
    "attorneys": "attorneys",
    "h1": "heading",
    "h2": "heading",
    "h3": "heading",
    "h4": "heading",
    "syllabus": "paragraph",
    "summary": "paragraph",
    "headnotes": "paragraph",
    "disposition": "paragraph",
    "parties": "paragraph",
}
INLINE_TAGS = {"em": "em", "i": "em", "strong": "strong", "b": "strong"}
# Elements whose entire content is dropped (page furniture).
DROP_TAGS = {"page-number", "page", "script", "style"}
DROP_CLASS_SPAN = {"star-pagination"}
DROP_CLASS_A = {"page-label", "lbl"}  # CL page label; centralia note number
DROP_CLASS_DIV = {"pgbreak"}  # centralia "p. N" page marker
FOOTNOTE_CONTAINER = {"footnote"}  # Harvard <footnote label="n">
FOOTNOTE_DIV_CLASSES = {
    "footnote",
    "fn",
}  # Lawbox div.footnote, centralia div.fn
AUTHOR_DIV_CLASSES = {"byline"}  # centralia author line

FN_SENTINEL = (
    "\x00FN{label}\x02"  # replaced with a namespaced <sup> per writing
)
_FN_SENTINEL_RE = re.compile("\x00FN(.*?)\x02")
TAG_RE = re.compile(r"<[^>]+>")
_INLINE_TAG_RE = re.compile(r"</?(?:em|strong)>")


def _ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def case_name_from_aria(aria: str | None) -> str:
    """CourtListener's link carries `aria-description="Citation for case:
    Lujan v. Defenders of Wildlife"` (sometimes truncated with "...")."""
    if not aria:
        return ""
    return _ws(re.sub(r"^Citation for case:\s*", "", aria))


def cited_case_tag(
    cluster_id: str | None,
    label: str,
    case_name: str = "",
    group: int | None = None,
    manual: bool = False,
) -> str:
    """The demo's inline citation tag. `label` and `case_name` are plain
    text (escaped here). `group` is the citation-group display number from
    the extraction pipeline; without it the renderer numbers by cluster id."""
    attrs = []
    if group is not None:
        attrs.append(f' data-group="{group}"')
    if cluster_id:
        attrs.append(f' data-cluster-id="{cluster_id}"')
    if case_name:
        attrs.append(f' data-case="{html.escape(case_name, quote=True)}"')
    if manual:
        attrs.append(' data-manual="1"')
    return f"<citedCase{''.join(attrs)}>{html.escape(label, quote=False)}</citedCase>"


# ── Citation-group state (from the extraction pipeline) ───────────────────
# `group_state` for one writing: {"occ": {idx: group-or-None}, "groups":
# {gid: {"n", "name", "cluster"}}}. `occ` is keyed by the index of the
# <span class="citation…"> in the writing's html, in document order, with
# the group id the extraction assigned, or None when it removed the span
# (statute, record cite…).
def _group_for(
    group_state: dict[str, Any] | None, idx: int
) -> tuple[int | None, str | None, str, bool]:
    """(group number, cluster id, case name, removed?) for a span index."""
    if not group_state:
        return None, None, "", False
    occ = group_state["occ"]
    if idx not in occ:
        return None, None, "", False
    gid = occ[idx]
    if gid is None:
        return None, None, "", True
    g = group_state["groups"].get(gid, {})
    return g.get("n"), g.get("cluster"), g.get("name", ""), False


def plain_text(html_text: str) -> str:
    """The text of an html fragment, tags dropped, whitespace collapsed."""
    return _ws(html.unescape(TAG_RE.sub("", html_text)))


# ── Heading detection ─────────────────────────────────────────────────────
_ENUM_ONLY_RE = re.compile(r"^(?:[IVXLC]+|[A-Za-z]|\d{1,2})\.?$")
_ENUM_TITLE_RE = re.compile(r"^(?:[IVXLC]+|[A-Za-z]|\d{1,2})\.\s+\S")
_HEADING_MAX = 90


def _title_like(s: str) -> bool:
    """Short, or Title Case / ALL CAPS — a heading, not a sentence fragment
    ("Nationwide Claim—Breach of Implied Warranty" yes; "An officer's
    personal knowledge of facts and circumstances, in" no)."""
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", s)
    if not words:
        return False
    if len(words) <= 4:
        return True
    big = [w for w in words if len(w) >= 4]
    capitalised = sum(1 for w in big if w[0].isupper())
    return not big or capitalised / len(big) >= 0.75


def looks_like_heading(text: str) -> bool:
    """Harvard html tags no headings; promote short enumerated / all-caps
    lines ("I", "A", "II. ANALYSIS", "a. Diminution in value", "BACKGROUND")
    while leaving numbered prose paragraphs ("14. An officer's…") alone."""
    t = text.strip()
    if not t or len(t) > _HEADING_MAX or not re.search(r"[A-Za-z]", t):
        return False
    if _ENUM_ONLY_RE.match(t):
        return True
    if t.endswith((".", ";", ",", ":")):
        # "It is so ordered." / "Judge Davila noted:" are prose.
        return False
    if _ENUM_TITLE_RE.match(t):
        remainder = re.sub(r"^(?:[IVXLC]+|[A-Za-z]|\d{1,2})\.\s+", "", t)
        return _title_like(remainder)
    letters = re.sub(r"[^A-Za-z]", "", t)
    return len(letters) >= 3 and letters.isupper()


# ── Structured html parser ────────────────────────────────────────────────
class _OpinionHTML(HTMLParser):
    """Walk structured CourtListener / Centralia html and emit blocks."""

    def __init__(self, group_state: dict | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self.group_state = group_state
        self._span_idx = -1  # index of the current <span class="citation…">
        self.blocks: list[dict] = []
        self.footnotes: list[dict] = []
        self.opinion_type: str | None = None
        self._buf: list[str] = []
        self._block_type = "paragraph"
        self._drop_depth = 0
        self._inline_open: list[str] = []
        self._strong_only = True  # every char so far inside <strong>
        self._cite: dict | None = None
        self._fn: dict | None = None
        self._fn_div_depth = 0
        self._pending_mark = ""
        self._mark_text: list[str] = []
        self._author_div = False

    # -- buffer helpers --------------------------------------------------
    def _target(self) -> list[str]:
        return self._fn["buf"] if self._fn is not None else self._buf

    def _close_inline(self) -> None:
        for tag in reversed(self._inline_open):
            self._target().append(f"</{tag}>")
        self._inline_open = []

    def _flush(self) -> None:
        self._close_inline()
        if self._fn is not None:
            text = _ws("".join(self._fn["buf"]))
            self._fn["buf"] = []
            if plain_text(text):
                self._fn["paras"].append(text)
            return
        text = _ws("".join(self._buf))
        self._buf = []
        strong_only = self._strong_only
        self._strong_only = True
        if not plain_text(text):
            return
        btype = self._block_type
        # Centralia / Lawbox put a heading inside the author line
        # ("William H. Orrick, United States District Judge INTRODUCTION").
        if btype == "author":
            m = re.match(r"^(.*?)\s*<strong>([^<]+)</strong>\s*$", text)
            if m and plain_text(m.group(1)):
                self.blocks.append(
                    {"type": "author", "html": m.group(1).strip()}
                )
                self.blocks.append(
                    {"type": "heading", "html": m.group(2).strip()}
                )
                return
            # An <author> line is often the subject of the sentence the next
            # <p> continues; merge when the continuation starts lowercase.
            self.blocks.append({"type": "author", "html": text})
            return
        if (
            btype == "paragraph"
            and self.blocks
            and self.blocks[-1]["type"] == "author"
            and plain_text(text)[:1].islower()
        ):
            self.blocks[-1]["html"] = f"{self.blocks[-1]['html']} {text}"
            return
        if (
            btype == "judges"
            and self.blocks
            and self.blocks[-1]["type"] == "author"
        ):
            # "Justice Kennedy, with whom" / "Justice White joins, concurring…"
            prev = plain_text(self.blocks[-1]["html"])
            if prev.endswith((",", "whom")):
                self.blocks[-1]["html"] = f"{self.blocks[-1]['html']} {text}"
                return
        if btype == "paragraph":
            plain = plain_text(text)
            if (
                strong_only and len(plain) <= _HEADING_MAX
            ) or looks_like_heading(plain):
                btype = "heading"
        if btype == "heading":
            # Headings carry no inline emphasis of their own.
            text = _ws(_INLINE_TAG_RE.sub("", text))
        self.blocks.append({"type": btype, "html": text})

    def _close_footnote(self) -> None:
        if self._fn is None:
            return
        self._flush()
        paras = self._fn["paras"]
        if paras:
            paras[0] = re.sub(r"^[.\s]+", "", paras[0])
            self.footnotes.append(
                {
                    "label": self._fn["label"],
                    "html": " ".join(paras)
                    if len(paras) == 1
                    else "</p><p>".join(paras),
                }
            )
        self._fn = None

    # -- parser callbacks ------------------------------------------------
    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        a = dict(attrs)
        cls = a.get("class", "") or ""
        classes = set(cls.split())
        if self._drop_depth:
            self._drop_depth += 1
            return
        if (
            tag in DROP_TAGS
            or (tag == "span" and classes & DROP_CLASS_SPAN)
            or (tag == "a" and classes & DROP_CLASS_A)
            or (tag == "div" and classes & DROP_CLASS_DIV)
        ):
            self._drop_depth = 1
            return
        if tag == "opinion":
            self.opinion_type = a.get("type")
            return
        if tag in FOOTNOTE_CONTAINER or (
            tag == "div" and classes & FOOTNOTE_DIV_CLASSES
        ):
            self._flush()
            id_num = re.search(r"(\d+)$", a.get("id", "") or "")
            label = (
                a.get("label") or (id_num.group(1) if id_num else "") or "*"
            )
            self._fn = {"label": label, "paras": [], "buf": []}
            self._fn_div_depth = 1
            return
        if self._fn is not None and tag == "div":
            self._fn_div_depth += 1
        if tag == "div" and classes & AUTHOR_DIV_CLASSES:
            self._flush()
            self._block_type = "author"
            self._author_div = True
            return
        # Footnote marks: <footnotemark>n</footnotemark>, <a class="footnote">n</a>,
        # <sup class="fnmark"><a>n</a></sup>. Inside a footnote body the
        # Lawbox back-link is the note's own number: drop it.
        if (
            tag == "footnotemark"
            or (tag == "a" and cls == "footnote")
            or (tag == "sup" and "fnmark" in classes)
        ):
            if self._fn is not None and tag == "a":
                self._drop_depth = 1
                return
            self._pending_mark = tag
            self._mark_text = []
            return
        if tag == "span" and "citation" in classes:
            self._span_idx += 1
            if self.group_state:
                n, cluster, case, removed = _group_for(
                    self.group_state, self._span_idx
                )
                # Pipeline state decides: removed spans and spans the state
                # does not know stay plain text; everything else is tagged.
                self._cite = {
                    "cluster": cluster,
                    "case": case,
                    "text": [],
                    "group": n,
                    "plain": removed or n is None,
                }
            elif not (classes & {"no-link", "multiple-matches"}):
                self._cite = {
                    "cluster": None,
                    "case": "",
                    "text": [],
                    "group": None,
                    "plain": False,
                }
            else:
                self._cite = {
                    "cluster": None,
                    "case": "",
                    "text": [],
                    "group": None,
                    "plain": True,
                }
            return
        if tag == "a" and self._cite is not None:
            m = CITED_CASE_HREF_RE.match(a.get("href", "") or "")
            if m:
                self._cite["cluster"] = self._cite["cluster"] or m.group(1)
                self._cite["case"] = self._cite["case"] or case_name_from_aria(
                    a.get("aria-description")
                )
            return
        if (
            tag in INLINE_TAGS
            and self._cite is None
            and not self._pending_mark
        ):
            norm = INLINE_TAGS[tag]
            self._inline_open.append(norm)
            self._target().append(f"<{norm}>")
            return
        if tag in BLOCK_TYPE:
            self._flush()
            self._block_type = BLOCK_TYPE[tag]

    def handle_endtag(self, tag: str) -> None:
        if self._drop_depth:
            self._drop_depth -= 1
            return
        if self._pending_mark and (tag == self._pending_mark):
            label = _ws("".join(self._mark_text))
            self._pending_mark = ""
            if label:
                self._target().append(FN_SENTINEL.format(label=label))
            return
        if self._pending_mark:
            return  # inner tags of a mark (the <a> inside centralia's <sup>)
        if tag == "span" and self._cite is not None:
            text = _ws("".join(self._cite["text"]))
            cid, case, group, plain = (
                self._cite["cluster"],
                self._cite["case"],
                self._cite["group"],
                self._cite["plain"],
            )
            self._cite = None
            if text and not plain and (cid or group is not None):
                self._target().append(cited_case_tag(cid, text, case, group))
            else:
                self._target().append(html.escape(text, quote=False))
            return
        if tag == "div" and self._author_div and self._fn is None:
            self._author_div = False
            self._flush()
            self._block_type = "paragraph"
            return
        if tag in FOOTNOTE_CONTAINER:
            self._close_footnote()
            return
        if tag == "div" and self._fn is not None:
            self._fn_div_depth -= 1
            if self._fn_div_depth <= 0:
                self._close_footnote()
            return
        if tag in INLINE_TAGS:
            norm = INLINE_TAGS[tag]
            if norm in self._inline_open:
                # close back to this tag
                while self._inline_open:
                    t = self._inline_open.pop()
                    self._target().append(f"</{t}>")
                    if t == norm:
                        break
            return
        if tag in BLOCK_TYPE:
            self._flush()
            self._block_type = "paragraph"

    def handle_data(self, data: str) -> None:
        if self._drop_depth:
            return
        if self._pending_mark:
            self._mark_text.append(data)
            return
        if self._cite is not None:
            self._cite["text"].append(data)
            return
        if (
            data.strip()
            and self._fn is None
            and "strong" not in self._inline_open
        ):
            self._strong_only = False
        self._target().append(html.escape(data, quote=False))

    def close(self) -> None:
        super().close()
        self._close_footnote()
        self._flush()


def structured_html_to_blocks(
    html_text: str, group_state: dict | None = None
) -> tuple[list[dict], list[dict], str | None]:
    """Return (blocks, footnotes, opinion type) for one writing."""
    parser = _OpinionHTML(group_state)
    html_text = re.sub(r"^\s*<\?xml[^>]*>\s*", "", html_text)
    parser.feed(html_text)
    parser.close()
    return parser.blocks, parser.footnotes, parser.opinion_type


# ── <pre class="inline"> flavour ──────────────────────────────────────────
_PRE_CITE_RE = re.compile(
    r'<span class="citation(?P<cls>[^"]*)"[^>]*>(?P<inner>.*?)</span>', re.S
)
_PAGE_NUMBER_LINE_RE = re.compile(r"^\s*(?:-\s*)?\d{1,3}\s*(?:-\s*)?$")
# "Page 3", "Page 3 of 18", "PAGE 12 – OPINION AND ORDER" (D. Or. footer)
_PAGE_LABEL_LINE_RE = re.compile(
    r"^\s*(?:Page|PAGE)\s+\d+(?:\s+of\s+\d+|\s*[–—-]\s*[A-Z][A-Z ,;&'.-]*)?\s*$"
)
# CM/ECF stamp: "Case 3:18-md-02828-SI   Document 130   Filed 03/27/20   Page 4 of 36"
_CASE_HEADER_LINE_RE = re.compile(
    r"^\s*Case\s+\d+:\d+-[a-z]{2}-\d+.*Page\s+\d+\s+of\s+\d+", re.I
)
_SHORT_LINE = 60  # chars; a shorter line may end a paragraph or be a heading


def _pre_cite_sub_factory(
    group_state: dict[str, Any] | None,
) -> Callable[[re.Match[str]], str]:
    counter = [-1]

    def sub(m: re.Match) -> str:
        counter[0] += 1
        classes = set(m.group("cls").split())
        inner = m.group("inner")
        text = plain_text(inner)
        href = re.search(r'href="(/opinion/(\d+)/[^"]*)"', inner)
        aria = re.search(r'aria-description="([^"]*)"', inner)
        case = (
            case_name_from_aria(html.unescape(aria.group(1))) if aria else ""
        )
        cid = href.group(2) if href else ""
        group = ""
        if group_state:
            n, cluster, gcase, removed = _group_for(group_state, counter[0])
            if removed or n is None:
                return text
            cid, case, group = cluster or cid, gcase or case, str(n)
        elif classes & {"no-link", "multiple-matches"} or not href:
            return text
        if not text:
            return text
        # Sentinel form; the tag is rebuilt after entity handling so the
        # label is escaped exactly once.
        return f"\x00CITE{cid}\x01{text}\x03{case}\x04{group}\x02"

    return sub


def _restore_cites(text: str) -> str:
    return re.sub(
        "\x00CITE(\\d*)\x01(.*?)\x03(.*?)\x04(\\d*)\x02",
        lambda m: cited_case_tag(
            m.group(1) or None,
            m.group(2),
            m.group(3),
            int(m.group(4)) if m.group(4) else None,
        ),
        text,
        flags=re.S,
    )


def pre_html_to_blocks(
    html_text: str, group_state: dict | None = None
) -> list[dict]:
    """Recover paragraphs (and obvious headings) from a pdftotext dump."""
    text = _PRE_CITE_RE.sub(_pre_cite_sub_factory(group_state), html_text)
    text = TAG_RE.sub("", text)  # <pre>, </pre>, stray <a>
    text = html.unescape(text)
    text = text.replace("\f", "\n\n")

    paragraphs: list[str] = []
    buf: list[str] = []
    prev_indent: int | None = None
    prev_short = False

    def flush() -> None:
        nonlocal prev_indent, prev_short
        if buf:
            joined = " ".join(buf)
            joined = re.sub(r"(\w)[-­] (?=[a-z])", r"\1", joined)
            paragraphs.append(_ws(joined))
            buf.clear()
        prev_indent = None
        prev_short = False

    for raw in text.split("\n"):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if (
            _PAGE_NUMBER_LINE_RE.match(stripped)
            or _PAGE_LABEL_LINE_RE.match(stripped)
            or _CASE_HEADER_LINE_RE.match(stripped)
        ):
            continue
        indent = len(line) - len(line.lstrip())
        short = len(stripped) < _SHORT_LINE
        columnar = bool(re.search(r"\S {4,}\S", stripped))
        if buf:
            indent_up = prev_indent is not None and indent > prev_indent + 1
            back_after_heading = (
                prev_short
                and prev_indent is not None
                and indent < prev_indent - 1
            )
            if indent_up or back_after_heading or columnar:
                flush()
        buf.append(stripped)
        prev_indent, prev_short = indent, short
        if columnar:
            flush()
    flush()

    blocks = []
    for p in paragraphs:
        if not p:
            continue
        escaped = _restore_cites(html.escape(p, quote=False))
        btype = (
            "heading"
            if looks_like_heading(plain_text(escaped))
            else "paragraph"
        )
        blocks.append({"type": btype, "html": escaped})
    return blocks


# ── Carrying CourtListener's resolved citations into other text ───────────
_CL_CITE_LINK_RE = re.compile(
    r'<span class="citation"[^>]*>\s*<a href="/opinion/(\d+)/[^"]*"'
    r'(?:[^>]*?aria-description="([^"]*)")?[^>]*>(.*?)</a>\s*</span>',
    re.S,
)
# "633 F.3d 894" / "504 U.S. 555, 561" / "2007 ME 130" — volume, reporter, page.
_REPORTER_CITE_RE = re.compile(r"^\d+\s+[A-Za-z][A-Za-z0-9.'\s-]*?\s+\d+")
_PROTECTED_RE = re.compile(r"<citedCase [^>]*>.*?</citedCase>|<[^>]+>", re.S)


def citation_map(cl_html_texts: list[str]) -> dict[str, tuple[str, str]]:
    """{reporter-cite text: (cluster id, case name)} from CourtListener's
    resolved citation links. Both the full link text ("633 F.3d 894, 899")
    and its base cite without the pin ("633 F.3d 894") are keys; short forms
    ("Id.", "Lujan, supra") are skipped — they cannot be matched by string."""
    out: dict[str, tuple[str, str]] = {}
    for h in cl_html_texts:
        for cid, aria, inner in _CL_CITE_LINK_RE.findall(h):
            text = plain_text(inner)
            if not _REPORTER_CITE_RE.match(text):
                continue
            case = case_name_from_aria(html.unescape(aria))
            out.setdefault(text, (cid, case))
            base = re.split(r",\s*(?:at\s+)?\d", text, maxsplit=1)[0].strip()
            if base != text:
                out.setdefault(base, (cid, case))
    return out


def _cite_pattern(text: str) -> re.Pattern:
    tokens = [re.escape(html.escape(t, quote=False)) for t in text.split()]
    return re.compile(r"(?<![\w.])" + r"\s+".join(tokens) + r"(?![\w])")


def inject_citations(
    block_html: str, cite_map: dict[str, tuple[str, str]]
) -> str:
    """Wrap known reporter cites in <citedCase> tags, longest match first.
    Existing tags (and their attributes) are never touched."""
    if not cite_map or not block_html:
        return block_html
    for text in sorted(cite_map, key=len, reverse=True):
        if text.split()[0] not in block_html:
            continue
        pat = _cite_pattern(text)
        cid, case = cite_map[text]
        pieces = _PROTECTED_RE.split(block_html)
        protected = _PROTECTED_RE.findall(block_html)
        pieces = [
            pat.sub(
                # m.group(0) is already-escaped html text; rebuild the tag
                # around it without escaping twice.
                lambda m, cid=cid, case=case: cited_case_tag(
                    cid, html.unescape(m.group(0)), case
                ),
                piece,
            )
            for piece in pieces
        ]
        rebuilt = pieces[0]
        for t, p in zip(protected, pieces[1:], strict=False):
            rebuilt += t + p
        block_html = rebuilt
    return block_html


# ── Public entry points ───────────────────────────────────────────────────
def is_pre_dump(html_text: str) -> bool:
    return html_text.lstrip()[:200].startswith("<pre")


def writing_label(cl_type: str, opinion_type: str | None, author: str) -> str:
    base = OPINION_TAG_LABEL.get(opinion_type or "") or CL_TYPE_LABEL.get(
        cl_type, "Opinion"
    )
    author = _ws(author or "")
    return f"{base} ({author})" if author else base


def writing_to_blocks(
    html_text: str, group_state: dict | None = None
) -> tuple[list[dict], list[dict], str | None]:
    """Dispatch on flavour. Returns (blocks, footnotes, opinion_type)."""
    if is_pre_dump(html_text):
        return pre_html_to_blocks(html_text, group_state), [], None
    return structured_html_to_blocks(html_text, group_state)


# ── The pipeline's added mentions (name-only references, Id., short forms) ─
# citation_seed.State locates a manual span by (writing, text, nth) in the
# writing's PLAIN text — `strip_to_text(html)`: block ends → newline, tags
# stripped, entities decoded — matched whitespace-insensitively. The same
# plain text is rebuilt here and each block's own plain text is located in
# it, so a span's plain offsets map onto one block's html.
_SEED_BLOCK_END = re.compile(
    r"</(p|div|blockquote|li|h[1-6])>|<br\s*/?>", re.I
)
_ENTITY_RE = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")
_CITED_CASE_SPAN_RE = re.compile(r"<citedCase[^>]*>.*?</citedCase>", re.S)


def strip_to_text(html_text: str) -> str:
    t = _SEED_BLOCK_END.sub("\n", html_text)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(t)


def _norm(text: str) -> str:
    """Whitespace runs → one space, leading whitespace dropped (the
    pipeline's norm_map)."""
    out, last_space = [], True
    for ch in text:
        if ch.isspace():
            if not last_space:
                out.append(" ")
                last_space = True
        else:
            out.append(ch)
            last_space = False
    return "".join(out)


def _find_nth_norm(
    norm_text: str, needle: str, nth: int
) -> tuple[int, int] | None:
    needle = re.sub(r"\s+", " ", needle).strip()
    if not needle:
        return None
    idx = -1
    for _ in range(nth + 1):
        idx = norm_text.find(needle, idx + 1)
        if idx < 0:
            return None
    return idx, idx + len(needle)


def _plain_positions(seg_html: str) -> tuple[str, list[int], list[int]]:
    """Plain text of a segment's html with, per plain char, the html start
    and end offsets of the source character or entity. Whitespace runs
    collapse to one space and leading whitespace is dropped, matching _norm."""
    plain: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    i, n = 0, len(seg_html)
    while i < n:
        ch = seg_html[i]
        if ch == "<":
            j = seg_html.find(">", i)
            tag = seg_html[i : (n if j < 0 else j + 1)]
            i = n if j < 0 else j + 1
            # a block boundary inside a segment (multi-paragraph footnote)
            # is whitespace in the pipeline's plain text
            if (
                _SEED_BLOCK_END.match(tag)
                and plain
                and not plain[-1].isspace()
            ):
                plain.append(" ")
                starts.append(i)
                ends.append(i)
            continue
        if ch == "&":
            m = _ENTITY_RE.match(seg_html, i)
            if m:
                for dch in html.unescape(m.group(0)):
                    plain.append(dch)
                    starts.append(i)
                    ends.append(m.end())
                i = m.end()
                continue
        if ch.isspace():
            if plain and not plain[-1].isspace():
                plain.append(" ")
                starts.append(i)
                ends.append(i + 1)
            i += 1
            continue
        plain.append(ch)
        starts.append(i)
        ends.append(i + 1)
        i += 1
    return "".join(plain), starts, ends


def inject_manual_mentions(
    segments: list[dict], writing_html: str, manual: list[dict], groups: dict
) -> int:
    """Tag the pipeline's added mentions in place. `segments` are the
    writing's blocks and footnotes in document order (each with "html");
    `manual` items carry text / nth / group (the pipeline's override
    schema). Returns the number of mentions tagged."""
    if not manual:
        return 0
    norm_t = _norm(strip_to_text(writing_html))
    # locate each segment's plain text inside the writing's plain text
    located: list[tuple[int, int, list[int], list[int]] | None] = []
    cursor = 0
    for seg in segments:
        plain, starts, ends = _plain_positions(seg["html"])
        plain = plain.rstrip()
        if not plain:
            located.append(None)
            continue
        pos = norm_t.find(plain, cursor)
        if (
            pos < 0 and len(plain) > 60
        ):  # a heading trimmed / merged author line
            pos = norm_t.find(plain[:60], cursor)
        if pos < 0:
            located.append(None)
            continue
        located.append((pos, pos + len(plain), starts, ends))
        cursor = pos + len(plain)
    inserts: dict[int, list[tuple[int, int, dict[str, Any]]]] = {}
    for m in manual:
        span = _find_nth_norm(norm_t, m.get("text", ""), int(m.get("nth", 0)))
        if not span:
            continue
        s, e = span
        for k, loc in enumerate(located):
            if not loc or not (loc[0] <= s and e <= loc[1]):
                continue
            starts, ends = loc[2], loc[3]
            ls, le = s - loc[0], e - loc[0]
            if le - 1 >= len(starts):
                break
            hs, he = starts[ls], ends[le - 1]
            seg_html = segments[k]["html"]
            # never nest inside / across an existing tag
            if any(
                a < he and hs < b
                for a, b in (
                    (t.start(), t.end())
                    for t in _CITED_CASE_SPAN_RE.finditer(seg_html)
                )
            ):
                break
            inner_tags = re.findall(r"<[^>]+>", seg_html[hs:he])
            # only inline emphasis may sit inside the span (handled below);
            # anything else (a footnote mark, a block end) is a real boundary
            if any(not _INLINE_TAG_RE.fullmatch(t) for t in inner_tags):
                break
            g = groups.get(m.get("group"), {})
            if g.get("n") is None:
                break
            inserts.setdefault(k, []).append((hs, he, g))
            break
    n_done = 0
    for k, items in inserts.items():
        seg_html = segments[k]["html"]
        # The pipeline can list the same span twice (a duplicated add) or
        # two spans that overlap ("Davis" inside "Davis v. Michigan …");
        # inserting both would split the first tag. Keep the first span at
        # each position, longest first, and drop anything it overlaps.
        accepted: list[tuple[int, int, dict[str, Any]]] = []
        for hs, he, g in sorted(items, key=lambda x: (x[0], -(x[1] - x[0]))):
            if any(a < he and hs < b for a, b, _ in accepted):
                continue
            accepted.append((hs, he, g))
        for hs, he, g in sorted(accepted, key=lambda x: x[0], reverse=True):
            mid = seg_html[hs:he]
            # Emphasis that opens or closes inside the span ("<em>McCulloch,
            # supra, </em>at 421") would be split by the tag: drop those
            # tags from the span and rebalance around it — a closing tag
            # moves before the citation, an opening tag after it.
            before_extra, after_extra = "", ""
            for t in re.findall(r"</?(?:em|strong)>", mid):
                if t.startswith("</"):
                    before_extra += t
                else:
                    after_extra = t + after_extra
            label = html.unescape(_INLINE_TAG_RE.sub("", mid))
            seg_html = (
                seg_html[:hs]
                + before_extra
                + cited_case_tag(
                    g.get("cluster"),
                    label,
                    g.get("name", ""),
                    g["n"],
                    manual=True,
                )
                + after_extra
                + seg_html[he:]
            )
            n_done += 1
        segments[k]["html"] = seg_html
    return n_done


def _namespace_footnotes(
    blocks: list[dict], footnotes: list[dict], w: int
) -> None:
    """Replace mark sentinels with linked <sup>s; give notes their ids."""
    known = {fn["label"] for fn in footnotes}

    def sup(m: re.Match) -> str:
        label = html.escape(m.group(1), quote=False)
        if m.group(1) not in known:
            return f'<sup class="fnref">{label}</sup>'
        return (
            f'<sup class="fnref" id="fnref-{w}-{label}">'
            f'<a href="#fn-{w}-{label}">{label}</a></sup>'
        )

    for b in blocks:
        b["html"] = _FN_SENTINEL_RE.sub(sup, b["html"])
    for fn in footnotes:
        fn["id"] = f"fn-{w}-{fn['label']}"
        fn["ref_id"] = f"fnref-{w}-{fn['label']}"
        fn["html"] = _FN_SENTINEL_RE.sub(sup, fn["html"])


def cluster_to_document_text(
    opinions: list[dict],
    cite_map: dict[str, tuple[str, str]] | None = None,
    citation_groups: dict | None = None,
) -> list[dict]:
    """Build the structured document for one cluster: a list of writings
    (see module docstring). `opinions` items need `html`, `type`, `author`
    (and `id` when `citation_groups` is given). A writing gets a title only
    when the cluster has more than one. `cite_map` (from `citation_map`)
    adds <citedCase> tags to text that has none of its own — Centralia's
    html. `citation_groups` is the extraction pipeline's state for this
    cluster: {"occurrences": {"<op_id>:<idx>": gid|None}, "manual": [...],
    "groups": {gid: {"n", "name", "cluster"}}} — when given, every
    citation carries the pipeline's group number and its removed spans stay
    plain text."""
    writings: list[dict] = []
    seen_titles: dict[str, int] = {}
    for w, op in enumerate(opinions, start=1):
        group_state = None
        if citation_groups:
            prefix = f"{op.get('id')}:"
            occ = {
                int(k[len(prefix) :]): v
                for k, v in citation_groups["occurrences"].items()
                if k.startswith(prefix)
            }
            group_state = {"occ": occ, "groups": citation_groups["groups"]}
        blocks, footnotes, opinion_type = writing_to_blocks(
            op["html"], group_state
        )
        if not blocks and not footnotes:
            continue
        if citation_groups:
            manual = [
                m
                for m in citation_groups.get("manual", [])
                if str(m.get("op_id")) == str(op.get("id"))
            ]
            inject_manual_mentions(
                blocks + footnotes,
                op["html"],
                manual,
                citation_groups["groups"],
            )
        elif cite_map and not any("<citedCase" in b["html"] for b in blocks):
            for b in blocks:
                b["html"] = inject_citations(b["html"], cite_map)
            for fn in footnotes:
                fn["html"] = inject_citations(fn["html"], cite_map)
        _namespace_footnotes(blocks, footnotes, w)
        title = None
        if len(opinions) > 1:
            title = writing_label(
                op.get("type", ""), opinion_type, op.get("author", "")
            )
            n = seen_titles.get(title, 0) + 1
            seen_titles[title] = n
            if n > 1:
                title = f"{title} {n}"
        writings.append(
            {"title": title, "blocks": blocks, "footnotes": footnotes}
        )
    return writings


def document_plain_paragraphs(document: list[dict] | str) -> list[str]:
    """Plain-text paragraphs (no markup) of a structured document, in
    reading order, paragraphs and block quotes only — for excerpts."""
    if isinstance(document, str):
        return [p.strip() for p in document.split("\n\n") if p.strip()]
    out = []
    for wr in document:
        for b in wr["blocks"]:
            if b["type"] in ("paragraph", "blockquote"):
                out.append(plain_text(b["html"]))
    return out
