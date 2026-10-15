# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""ContentDB adapter for the django-enrichment bus (contract A4 § 7).

The bus loads this module by dotted path from `settings.ENRICHMENT_ADAPTERS` and calls its functions by name. It
imports nothing from django-enrichment (or from the translator): the dependency points one way.

Conventions (opaque to the bus):

- `subject_ref`     = the draft's content uid (the uid the v1 draft API shows)
- `target_kind`     = `"attribute_value"` (a field of the draft) | `"document"` (create a new draft)
- `target_locator`  = `{"path": <field key>, "language": <iso2>}` (field; `language` optional) | `{"channel": <idx or "">}`
                      (document)
- `proposed_value`  = `{"text"}` (text path / text attribute) | `{"option"}` / `{"options"}` (select attributes)
                    | the document `{language, title, slug, body_markdown, meta, faq}` (document)
- `current_snapshot`= the same shape as the value, read raw from the draft; `{}` for a document

Field keys are paths (`content_path_service`) or `attributes.<slug>` (`content_attribute_service`). A draft has one
language: a locator that names another one is refused (`ValueError`) by `read_current` / `apply` / `revert`, so a
multi-language `write` run cannot put one language's text on a draft of another; `subject_languages` lets the
bus skip those languages before any AI call. A document `apply` returns `{"subject_ref": <new uid>}`; its `revert`
deletes that draft (`proposal.result_ref`) only while it was never published.
"""

import json

from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

from django_contentdb.enums import Action
from django_contentdb.models import ActivityLog, Content, ContentChannel, Draft, Language
from django_contentdb.services import content_attribute_service, content_path_service, document_service

DOCUMENT_KIND = "document"
ATTRIBUTE_PREFIX = "attributes."
CONTEXT_MAX_CHARS = 3000
_PAGE_SIZE = 100
_CONTEXT_FIELD_CAP = 300
_ALLOWED_FILTERS = {"content_type": "content_type__slug", "language": "language__iso2__iexact"}


def resolve_targets(scope_spec: dict, page: int = 1) -> list[str]:
    """`list` echoes a page of `refs`; `filter` pages the draft uids of a channel (optional `content_type`,
    `language` filters). An unknown filter key raises `ValueError` rather than widening the scope."""
    mode = scope_spec.get("mode")
    offset = (max(page, 1) - 1) * _PAGE_SIZE
    if mode == "list":
        return list(scope_spec.get("refs", [])[offset : offset + _PAGE_SIZE])
    if mode != "filter":
        raise ValueError(f"unsupported scope mode for contentdb adapter: {mode!r}")
    drafts = _filtered_drafts(scope_spec).order_by("pk")
    return [str(uid) for uid in drafts.values_list("content__uid", flat=True)[offset : offset + _PAGE_SIZE]]


def _filtered_drafts(scope_spec: dict):
    if not (channel := scope_spec.get("channel")):
        raise ValueError("filter scope needs a channel")
    filters = scope_spec.get("filters") or {}
    if unknown := set(filters) - _ALLOWED_FILTERS.keys():
        raise ValueError(f"unsupported contentdb filters: {sorted(unknown)}")
    lookups = {_ALLOWED_FILTERS[key]: value for key, value in filters.items()}
    return Draft.objects.filter(channels__idx=channel, **lookups)


def find_gaps(check: str, params: dict, scope: dict) -> list:
    """ContentDB defines no quality checks yet."""
    return []


def read_current(*, subject_ref: str, target_kind: str, target_locator: dict) -> dict:
    if target_kind == DOCUMENT_KIND:
        return {}
    path = target_locator["path"]
    content = _content(subject_ref, target_locator)
    if path.startswith(ATTRIBUTE_PREFIX):
        return content_attribute_service.read(content, _attribute(path))
    return {"text": content_path_service.read_text(content, path)}


def apply(proposal) -> dict | None:
    if proposal.target_kind == DOCUMENT_KIND:
        draft = document_service.create_draft(proposal.proposed_value, channel=_channel(proposal))
        _log(proposal, draft.content, Action.CREATE)
        return {"subject_ref": str(draft.content.uid)}
    _write(proposal, proposal.proposed_value)
    return None


def revert(proposal) -> None:
    if proposal.target_kind != DOCUMENT_KIND:
        _write(proposal, proposal.current_snapshot or {"text": ""})
        return
    draft = Draft.objects.filter(content__uid=proposal.result_ref).first() if proposal.result_ref else None
    if draft is None:
        return
    _log(proposal, draft.content, Action.DELETE)
    document_service.delete_draft(draft)


def _write(proposal, value: dict) -> None:
    path = proposal.target_locator["path"]
    content = _content(proposal.subject_ref, proposal.target_locator)
    if path.startswith(ATTRIBUTE_PREFIX):
        content_attribute_service.write(content, _attribute(path), value)
    else:
        content_path_service.write_text(content, path, value.get("text"))
    _log(proposal, content, Action.UPDATE)


def _log(proposal, content: Content, action: str) -> None:
    """Audit the write as the reviewer; a proposal without one (system apply) is not logged."""
    if reviewer := getattr(proposal, "reviewed_by", None):
        ActivityLog.objects.create(user=reviewer, target=content, action=action)


def _channel(proposal) -> str:
    return (proposal.target_locator or {}).get("channel") or ""


def _content(subject_ref: str, locator: dict | None = None) -> Content:
    try:
        content = (
            Content.objects.select_related("draft__content_type__attribute_set", "draft__language")
            .filter(uid=subject_ref)
            .first()
        )
    except ValidationError:
        content = None
    if content is None or not hasattr(content, "draft"):
        raise ValueError(f"draft {subject_ref!r} not found")
    _check_language(content, (locator or {}).get("language"))
    return content


def _check_language(content: Content, language: str | None) -> None:
    draft_language = content.draft.language.iso2.lower()
    if language and language.lower() != draft_language:
        raise ValueError(f"draft {content.uid} is in {draft_language!r}, not {language!r}")


def _attribute(path: str):
    return content_attribute_service.get_attribute(path.removeprefix(ATTRIBUTE_PREFIX))


def describe_fields(*, channel: str, language: str = "", subject_ref: str = "") -> list[dict]:
    """Static text fields, content-type attributes and — with `subject_ref` — that draft's section/tile texts.

    Labels are English whatever `language` (ContentDB keeps no translated field labels).
    """
    fields = content_path_service.static_fields() + content_attribute_service.describe()
    if subject_ref:
        fields += content_path_service.part_fields(_content(subject_ref).content or {})
    return fields


def channel_languages(*, channel: str) -> list[str]:
    """The channel's default language first, then the other languages of its drafts (lowercase iso2)."""
    record = ContentChannel.objects.select_related("default_language").get(idx=channel)
    main = record.default_language.iso2.lower() if record.default_language else ""
    used = Language.objects.filter(draft__channels=record).values_list("iso2", flat=True).distinct()
    others = sorted({iso2.lower() for iso2 in used} - {main})
    return [main, *others] if main else others


def subject_languages(*, subject_ref: str) -> list[str]:
    """The draft's one language (lowercase iso2): a `write` over every channel language skips the others."""
    return [_content(subject_ref).draft.language.iso2.lower()]


def make_locator(*, field_key: str, channel: str, language: str | None) -> dict:
    """`{"path": field_key, "language": language}` — the draft's channels need no key; the language is checked
    against the draft's own on read and write. A language-less call (`pick`) gives `{"path": field_key}`."""
    if field_key.startswith(ATTRIBUTE_PREFIX):
        _attribute(field_key)
    elif not content_path_service.is_text_path(field_key):
        raise ValueError(f"unknown contentdb field {field_key!r}")
    return {"path": field_key, "language": language.lower()} if language else {"path": field_key}


def field_key(*, locator: dict) -> str | None:
    return locator.get("path")


def build_context(*, subject_ref: str, channel: str, language: str) -> dict:
    """Plain-text facts of the draft for an AI prompt, at most `CONTEXT_MAX_CHARS` as JSON."""
    content = _content(subject_ref)
    context = {
        "uid": str(content.uid),
        "content_type": content.draft.content_type.slug,
        "name": _cap(content.draft.name, _CONTEXT_FIELD_CAP),
        "route": next(iter(content.draft.routes.values_list("url", flat=True)), ""),
        "seo_title": _cap(content_path_service.read_text(content, "meta.title"), _CONTEXT_FIELD_CAP),
        "seo_description": _cap(content_path_service.read_text(content, "meta.description"), _CONTEXT_FIELD_CAP),
        "text": "",
    }
    context["text"] = _page_text(content)
    while (overflow := len(json.dumps(context, ensure_ascii=False)) - CONTEXT_MAX_CHARS) > 0:
        context["text"] = _cap(context["text"], len(context["text"]) - overflow)
    return context


def _page_text(content: Content) -> str:
    fields = content_path_service.part_fields(content.content or {})
    texts = (content_path_service.read_text(content, field["key"]) for field in fields)
    return " ".join(_plain(text) for text in texts)


def _plain(text: str) -> str:
    return " ".join(strip_tags(text).split())


def _cap(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}…"
