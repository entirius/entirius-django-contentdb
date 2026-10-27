# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Text fields of a draft addressed by a dotted path — read, write (merge + sanitise) and list.

Paths:

- `name`                                          — the draft name
- `meta.<field>` / `extension.<field>`            — SEO meta and the blog header (static fields below)
- `content.sections.<uid>.<title|description>`    — one text prop of a section
- `content.tiles.<uid>.<title|description>`       — one text prop of a tile

A write changes only the addressed key: the rest of the JSON is kept as stored. Markup is sanitised with the
editor allowlist (`content_service.sanitize_content`). The section/tile listing is a small port of the
contentdb-translator extractor (title and description of every section and tile that has text).
"""

import re
from dataclasses import dataclass

from django_contentdb.models import Content
from django_contentdb.services.content_service import sanitize_content

NAME_MAX_LENGTH = 128


@dataclass(frozen=True)
class TextField:
    label: str
    type: str
    max_length: int | None


STATIC_FIELDS = {
    "name": TextField("Name", "text", NAME_MAX_LENGTH),
    "meta.title": TextField("SEO title", "text", 60),
    "meta.description": TextField("SEO description", "text", 160),
    "meta.og_title": TextField("Open Graph title", "text", 90),
    "meta.og_description": TextField("Open Graph description", "text", 200),
    "extension.title": TextField("Header title", "text", None),
    "extension.description": TextField("Header description", "text", None),
}
_CONTENT_PATH = re.compile(r"^content\.(sections|tiles)\.([\w-]+)\.(title|description)$")
_PART_FIELDS = {"title": TextField("title", "text", None), "description": TextField("description", "html", None)}
_PART_LABELS = {"sections": "Section", "tiles": "Tile"}
_ORDER_KEYS = {"sections": "sections_order", "tiles": "tiles_order"}


def is_text_path(path: str) -> bool:
    return path in STATIC_FIELDS or bool(_CONTENT_PATH.match(path))


def read_text(content: Content, path: str) -> str:
    """The stored string at `path`, "" when the key is missing or not a string."""
    if path == "name":
        return content.draft.name
    root, *keys = _keys(path)
    node = getattr(content, root) or {}
    for key in keys:
        node = node.get(key) if isinstance(node, dict) else None
    return node if isinstance(node, str) else ""


def write_text(content: Content, path: str, text: str) -> None:
    """Set the string at `path`, keeping every other key of the JSON. A missing section/tile or a non-string value
    raises `ValueError`."""
    if not isinstance(text, str):
        raise ValueError(f"{path!r} expects a string value")
    text = sanitize_content(text)
    if path == "name":
        _write_name(content, text)
        return
    root, *keys = _keys(path)
    data = getattr(content, root) or {}
    parent = data
    for key in keys[:-1]:
        parent = parent.get(key) if isinstance(parent, dict) else None
    if not isinstance(parent, dict):
        raise ValueError(f"path {path!r} does not exist in this draft")
    parent[keys[-1]] = text
    setattr(content, root, data)
    content.save(update_fields=[root, "updated_at"])


def _write_name(content: Content, text: str) -> None:
    if len(text) > NAME_MAX_LENGTH:
        raise ValueError(f"name longer than {NAME_MAX_LENGTH} characters")
    content.draft.name = text
    content.draft.save(update_fields=["name"])


def _keys(path: str) -> list[str]:
    if not is_text_path(path):
        raise ValueError(f"unknown text path {path!r}")
    return path.split(".")


def part_fields(content_json: dict) -> list[dict]:
    """Catalog entries for the section and tile texts of one draft, in page order."""
    fields = []
    for part in ("sections", "tiles"):
        for position, uid in enumerate(_ordered_uids(content_json, part), start=1):
            fields.extend(_part_entries(part, uid, position, content_json[part][uid]))
    return fields


def _ordered_uids(content_json: dict, part: str) -> list[str]:
    items = content_json.get(part)
    if not isinstance(items, dict):
        return []
    order = content_json.get(_ORDER_KEYS[part])
    ordered = [uid for uid in order if uid in items] if isinstance(order, list) else []
    return ordered + [uid for uid in items if uid not in ordered]


def _part_entries(part: str, uid: str, position: int, data) -> list[dict]:
    if not isinstance(data, dict):
        return []
    kind = data.get("core_type") or part
    entries = []
    for prop, shape in _PART_FIELDS.items():
        if isinstance(text := data.get(prop), str) and text.strip():
            label = f"{_PART_LABELS[part]} {position} ({kind}) {shape.label}"
            entries.append(_entry(f"content.{part}.{uid}.{prop}", TextField(label, shape.type, None)))
    return entries


def static_fields() -> list[dict]:
    return [_entry(path, field) for path, field in STATIC_FIELDS.items()]


def _entry(path: str, field: TextField) -> dict:
    return {
        "key": path,
        "label": field.label,
        "type": field.type,
        "max_length": field.max_length,
        "translatable": True,
    }
