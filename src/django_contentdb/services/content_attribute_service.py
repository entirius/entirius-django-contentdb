# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Content-type attributes of a draft as enrichment fields — catalog, read and write by slug.

An attribute closed to new values (`allow_new_values=False`) is a select of its existing values (multiselect when
`allow_many_values`); an open text attribute (`is_txt` / `is_txt_long`, one value) is a text field. Other
attributes (bool, datetime, open multi-value) are not offered. Option values are the stored values as strings.

Values: `{"text": str}` (text), `{"option": str}` (select, "" = none), `{"options": [str, ...]}` (multiselect).
"""

from django_contentdb.models import Attribute, AttributeValue, Content, ContentAttribute

MAX_OPTIONS = 200
_SELECT_VALUE_TYPES = ("is_txt", "is_txt_long", "is_int")
_TEXT_LIMITS = {"is_txt": 128, "is_txt_long": 2048}


def field_type(attribute: Attribute) -> str | None:
    """`select` / `multiselect` / `text`, or None when the attribute is not offered."""
    if not attribute.allow_new_values and any(getattr(attribute, flag) for flag in _SELECT_VALUE_TYPES):
        return "multiselect" if attribute.allow_many_values else "select"
    if _text_limit(attribute) and not attribute.allow_many_values:
        return "text"
    return None


def describe() -> list[dict]:
    """Catalog entries of every offered attribute that belongs to an attribute set (`attributes.<slug>`)."""
    attributes = Attribute.objects.filter(attribute_sets__isnull=False).distinct().order_by("slug")
    return [_describe(attribute, kind) for attribute in attributes if (kind := field_type(attribute))]


def _describe(attribute: Attribute, kind: str) -> dict:
    entry = {
        "key": f"attributes.{attribute.slug}",
        "label": attribute.label,
        "type": kind,
        "max_length": _text_limit(attribute) if kind == "text" else None,
        "translatable": kind == "text",
    }
    if kind != "text":
        options = [str(value.value) for value in attribute.values.order_by("pk")[: MAX_OPTIONS + 1]]
        entry["options"] = [{"value": option, "label": option} for option in options[:MAX_OPTIONS]]
        entry["options_truncated"] = len(options) > MAX_OPTIONS
    return entry


def get_attribute(slug: str) -> Attribute:
    attribute = Attribute.objects.filter(slug=slug).first()
    if attribute is None or field_type(attribute) is None:
        raise ValueError(f"attribute {slug!r} is not a writable field")
    return attribute


def read(content: Content, attribute: Attribute) -> dict:
    values = sorted(
        str(link.attribute_value.value)
        for link in _links(content, attribute).select_related("attribute_value__attribute")
    )
    kind = field_type(attribute)
    if kind == "multiselect":
        return {"options": values}
    if kind == "select":
        return {"option": values[0] if values else ""}
    return {"text": values[0] if values else ""}


def write(content: Content, attribute: Attribute, value: dict) -> None:
    """Replace the draft's values of `attribute` with `value`; the attribute must be in the draft's set."""
    if not content.draft.content_type.attribute_set.attributes.filter(pk=attribute.pk).exists():
        raise ValueError(f"attribute {attribute.slug!r} does not belong to this content type")
    new_values = _values(attribute, value)
    _links(content, attribute).delete()
    ContentAttribute.objects.bulk_create(ContentAttribute(content=content, attribute_value=v) for v in new_values)


def _links(content: Content, attribute: Attribute):
    return ContentAttribute.objects.filter(content=content, attribute_value__attribute=attribute)


def _values(attribute: Attribute, value: dict) -> list[AttributeValue]:
    kind = field_type(attribute)
    if kind == "text":
        return _text_value(attribute, _string(attribute, value.get("text")))
    requested = value.get("options") if kind == "multiselect" else [value.get("option")]
    return [_option(attribute, str(option)) for option in requested or [] if option not in (None, "")]


def _string(attribute: Attribute, text) -> str:
    if not isinstance(text, str):
        raise ValueError(f"attribute {attribute.slug!r} expects a string value")
    return text


def _text_value(attribute: Attribute, text: str) -> list[AttributeValue]:
    if not text:
        return []
    if len(text) > _text_limit(attribute):
        raise ValueError(f"attribute {attribute.slug!r} takes at most {_text_limit(attribute)} characters")
    stored, _ = AttributeValue.objects.get_or_create(attribute=attribute, **{f"value_{attribute.type_as_str}": text})
    return [stored]


def _option(attribute: Attribute, option: str) -> AttributeValue:
    for stored in attribute.values.all():
        if str(stored.value) == option:
            return stored
    raise ValueError(f"{option!r} is not an option of attribute {attribute.slug!r}")


def _text_limit(attribute: Attribute) -> int | None:
    return next((limit for flag, limit in _TEXT_LIMITS.items() if getattr(attribute, flag)), None)
