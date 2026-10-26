# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Stored page HTML is sanitised on write.

Rich-text props of sections and tiles (``description``, ``header_area``, ``footer_area``, rich-text fields of group
props such as an accordion item) are rendered as HTML by the CMS and the storefront. Which props are rich text is
decided by the CMS configuration, not by this module, so every string of the content JSON that carries markup goes
through the allowlist; a string without markup is stored as sent.

The allowlist is what the CMS editor writes. Output is rebuilt from parsed tokens: text and attribute values are
escaped, everything outside the allowlist is dropped (a dropped tag keeps its text, ``script`` and ``style`` lose it).
"""

import html
import re
from html.parser import HTMLParser
from typing import Any

_ALLOWED_TAGS = frozenset(
    "h1 h2 h3 h4 h5 h6 p br hr div span blockquote pre code ul ol li a img strong b em i u s del mark sub sup "
    "table thead tbody tfoot tr th td colgroup col".split()
)
_VOID_TAGS = frozenset({"br", "hr", "img", "col"})
_DROPPED_WITH_CONTENT = frozenset({"script", "style"})
_ALLOWED_ATTRS = frozenset(
    "href target rel src alt title width height style colspan rowspan colwidth data-color data-faq-tooltip".split()
)
# A URL attribute keeps a value without a scheme (a path, an anchor) or with one of these.
_URL_SCHEMES = {"href": frozenset({"http", "https", "mailto"}), "src": frozenset({"http", "https"})}
_SCHEME_RE = re.compile(r"^([a-z][a-z0-9+.-]*):")
# Browsers drop control characters and whitespace before they read the scheme ("java\tscript:").
_URL_NOISE_RE = re.compile(r"[\x00-\x20\x7f-\x9f]")
# Alignment, colours and table column widths; no position or size that could lay content over the page, and no
# value that could load anything (a url needs a character outside the set).
_STYLE_PROPS = frozenset({"text-align", "color", "background-color", "width", "min-width"})
_STYLE_VALUE_RE = re.compile(r"^[\w\s#.,%()-]+$", re.ASCII)
_MARKUP_RE = re.compile(r"<[a-zA-Z/!?]")


def _safe_url(name: str, value: str) -> bool:
    scheme = _SCHEME_RE.match(_URL_NOISE_RE.sub("", value).lower())
    return scheme is None or scheme.group(1) in _URL_SCHEMES[name]


def _safe_style(value: str) -> str:
    kept = []
    for declaration in value.split(";"):
        prop, _, prop_value = declaration.partition(":")
        if prop.strip().lower() in _STYLE_PROPS and _STYLE_VALUE_RE.match(prop_value.strip()):
            kept.append(f"{prop.strip().lower()}: {prop_value.strip()}")
    return "; ".join(kept)


def _safe_attrs(tag: str, attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    kept: dict[str, str] = {}
    for name, value in attrs:
        if name not in _ALLOWED_ATTRS or name in kept:
            continue
        value = _safe_style(value or "") if name == "style" else value or ""
        if (name in _URL_SCHEMES and not _safe_url(name, value)) or (name == "style" and not value):
            continue
        kept[name] = value
    if tag == "a" and "target" in kept:
        kept["rel"] = "noopener noreferrer"
    return kept


class _AllowlistSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._dropping: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _DROPPED_WITH_CONTENT:
            self._dropping = tag
        if self._dropping or tag not in _ALLOWED_TAGS:
            return
        rendered = "".join(f' {name}="{html.escape(value)}"' for name, value in _safe_attrs(tag, attrs).items())
        self._parts.append(f"<{tag}{rendered}>")

    def handle_endtag(self, tag: str) -> None:
        if self._dropping:
            self._dropping = None if tag == self._dropping else self._dropping
        elif tag in _ALLOWED_TAGS and tag not in _VOID_TAGS:
            self._parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self._dropping:
            self._parts.append(html.escape(data, quote=False))

    def get_output(self) -> str:
        return "".join(self._parts)


def sanitize_html(text: str) -> str:
    """Return ``text`` with only the editor's tags, attributes, URL schemes and style properties."""
    parser = _AllowlistSanitizer()
    parser.feed(text)
    parser.close()
    return parser.get_output()


def sanitize_content(value: Any) -> Any:
    """Sanitise every markup-bearing string of a content JSON value, at any depth; other values are returned as is."""
    if isinstance(value, str):
        return sanitize_html(value) if _MARKUP_RE.search(value) else value
    if isinstance(value, dict):
        return {key: sanitize_content(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_content(item) for item in value]
    return value
