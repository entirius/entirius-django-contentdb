# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Article markdown + meta → blog-post payload (pure functions, no ORM, no network).

Blog model: a flat list of sections (`section-text`, `section-faq`), no tiles. Markdown images are dropped (the MVP
has no image pipeline), but an image still ends the text section before it, as in the original converter. The payload has the shape the v1 draft API accepts: `name`, `language`, `routes`, `meta`,
`extension`, `content`.
"""

import re
import uuid

# The FAQ heading: "## FAQ" from the pipeline, translated variants ("FAQs", "Frequently asked questions") and the
# Polish import heading.
FAQ_HEADING = re.compile(r"^\s*faqs?\b|na jakie pytania|frequently asked", re.I)
FAQ_TITLES = {"pl": "Na jakie pytania znajdziesz odpowiedź w tym artykule?"}
DEFAULT_FAQ_TITLE = "Questions answered in this article"
_DATE_LINE = re.compile(r"^Data (publikacji|aktualizacji):")
_BLOCK_START = re.compile(r"^(#{1,4}\s|!\[|\||[-*]\s)")
_LIST_MARKERS = ("- ", "* ")
_SPACER = "<p></p>"


def inline(text: str) -> str:
    """Inline markdown (**bold**, *italic*, [link](url), `code`) → HTML."""
    text = text.strip()
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


def tokenize(md: str) -> list[dict]:
    """Split markdown into blocks: heading / image / list / table / para."""
    blocks: list[dict] = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        i = _consume_block(lines, i, blocks)
    return blocks


def _consume_block(lines: list[str], i: int, blocks: list[dict]) -> int:
    line = lines[i].rstrip()
    if heading := re.match(r"^(#{1,4})\s+(.*)$", line):
        blocks.append({"t": "heading", "level": len(heading.group(1)), "text": heading.group(2).strip()})
        return i + 1
    if image := re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line):
        blocks.append({"t": "image", "alt": image.group(1).strip(), "url": image.group(2).strip()})
        return i + 1
    if line.lstrip().startswith(_LIST_MARKERS):
        return _consume_list(lines, i, blocks)
    if line.lstrip().startswith("|"):
        return _consume_table(lines, i, blocks)
    return _consume_para(lines, i, blocks)


def _consume_list(lines: list[str], i: int, blocks: list[dict]) -> int:
    items = []
    while i < len(lines) and lines[i].lstrip().startswith(_LIST_MARKERS):
        items.append(lines[i].lstrip()[2:].strip())
        i += 1
    blocks.append({"t": "list", "items": items})
    return i


def _consume_table(lines: list[str], i: int, blocks: list[dict]) -> int:
    rows = []
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        rows.append([cell.strip() for cell in lines[i].strip().strip("|").split("|")])
        i += 1
    rows = [row for row in rows if not all(set(cell) <= set("-: ") for cell in row)]  # drop the separator
    blocks.append({"t": "table", "rows": rows})
    return i


def _consume_para(lines: list[str], i: int, blocks: list[dict]) -> int:
    buf = []
    while i < len(lines) and lines[i].strip() and not _BLOCK_START.match(lines[i].lstrip()):
        buf.append(lines[i].strip())
        i += 1
    blocks.append({"t": "para", "text": " ".join(buf)})
    return i


def block_html(block: dict) -> str:
    if block["t"] == "heading":
        return f"<h{block['level']}>{inline(block['text'])}</h{block['level']}>"
    if block["t"] == "para":
        return f"<p>{inline(block['text'])}</p>"
    if block["t"] == "list":
        return "<ul>" + "".join(f"<li><p>{inline(item)}</p></li>" for item in block["items"]) + "</ul>"
    if block["t"] == "table":
        return _table_html(block["rows"])
    return ""


def _table_html(rows: list[list[str]]) -> str:
    head, *body = rows
    thead = "<tr>" + "".join(f"<th>{inline(cell)}</th>" for cell in head) + "</tr>"
    tbody = "".join("<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>" for row in body)
    return f"<table><thead>{thead}</thead><tbody>{tbody}</tbody></table>"


def blocks_html(blocks: list[dict]) -> str:
    """Join blocks with empty `<p></p>` spacers: after every heading, and before a heading that follows a list or
    a table."""
    out: list[str] = []
    for i, block in enumerate(blocks):
        previous = blocks[i - 1] if i else None
        if block["t"] == "heading" and previous and previous["t"] in ("list", "table"):
            out.append(_SPACER)
        out.append(block_html(block))
        if block["t"] == "heading":
            out.append(_SPACER)
    return "".join(out)


def split_article(md: str) -> dict:
    """H1 → title; date lines and the hero image dropped; the rest → body, everything after the FAQ heading → faq."""
    blocks = tokenize(md)
    title = next((b["text"] for b in blocks if b["t"] == "heading" and b["level"] == 1), "")
    hero = _find_hero(blocks)
    body: list[dict] = []
    faq: list[dict] = []
    in_faq = False
    for block in blocks:
        if block is hero or _skipped(block):
            continue
        if block["t"] == "heading" and block["level"] == 2 and FAQ_HEADING.search(block["text"]):
            in_faq = True
            continue
        (faq if in_faq else body).append(block)
    return {"title": title, "body": body, "faq": faq}


def _find_hero(blocks: list[dict]) -> dict | None:
    """The hero is the first image before the first section heading (##)."""
    for block in blocks:
        if block["t"] == "heading" and block["level"] >= 2:
            return None
        if block["t"] == "image":
            return block
    return None


def _skipped(block: dict) -> bool:
    if block["t"] == "heading" and block["level"] == 1:
        return True
    return block["t"] == "para" and bool(_DATE_LINE.match(block["text"]))


def build_sections(body: list[dict]) -> dict[str, dict]:
    """Body → `section-text` sections; an image ends the current section (the image itself is dropped)."""
    sections: dict[str, dict] = {}
    buf: list[dict] = []
    for block in [*body, {"t": "image"}]:
        if block["t"] != "image":
            buf.append(block)
            continue
        if buf:
            sections[_uid()] = {"core_type": "section-text", "title": None, "description": blocks_html(buf)}
        buf = []
    return sections


def build_faq(faq_blocks: list[dict], language: str) -> dict | None:
    """`### question` + the blocks up to the next `###` → `faq_items`."""
    items: list[dict] = []
    question, answer = None, []
    for block in faq_blocks:
        if block["t"] == "heading" and block["level"] == 3:
            _add_faq_item(items, question, answer)
            question, answer = block["text"], []
        else:
            answer.append(block)
    _add_faq_item(items, question, answer)
    if not items:
        return None
    title = FAQ_TITLES.get(language.lower(), DEFAULT_FAQ_TITLE)
    return {"core_type": "section-faq", "title": title, "faq_items": items}


def _add_faq_item(items: list[dict], question: str | None, answer: list[dict]) -> None:
    if question:
        items.append({"question": question, "answer": blocks_html(answer)})


def first_paragraph(body: list[dict]) -> str:
    text = re.sub(r"\*\*|\*|`", "", next((b["text"] for b in body if b["t"] == "para"), ""))
    return (text[:157] + "…") if len(text) > 158 else text


def build_payload(md: str, meta: dict, *, slug: str) -> dict:
    """Full blog-post payload. `meta` keys: `lang`, `title`, `seo_title`, `seo_description`, `og_title`,
    `og_description` (all optional)."""
    article = split_article(md)
    title = article["title"] or meta.get("title", "")
    seo_title = meta.get("seo_title") or title
    seo_description = meta.get("seo_description") or first_paragraph(article["body"])
    language = meta.get("lang", "en")
    return {
        "name": title,
        "language": language.upper(),
        "routes": [slug] if slug else [],
        "meta": {
            "index": "Index",
            "follow": "Follow",
            "title": seo_title,
            "description": seo_description,
            "og_title": meta.get("og_title") or seo_title,
            "og_description": meta.get("og_description") or seo_description,
            "og_image": "",
        },
        "extension": {
            "reset": False,
            "title": title,
            "core_type": "tile-blog-extension",
            "images_set": {},
            "description": seo_description,
        },
        "content": _content(article, language),
    }


def _content(article: dict, language: str) -> dict:
    sections = build_sections(article["body"])
    if faq := build_faq(article["faq"], language):
        sections[_uid()] = faq
    return {
        "document_configs": {},
        "sections": sections,
        "sections_order": list(sections),
        "tiles": {},
        "tiles_order": {},
    }


def _uid() -> str:
    return str(uuid.uuid4())
