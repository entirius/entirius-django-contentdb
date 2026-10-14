# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Create an unpublished blog-post draft from an article document, and delete it again while never published.

Document value (contract A4 § 6, `compose`): `{language, title, slug, body_markdown, meta, faq}` where `meta` is
`{title, description, og_title, og_description}` and `faq` is `[{question, answer}]` (answers in markdown). The
payload comes from `article_converter.build_payload`; the route is the slug, suffixed `-2`, `-3`, … when taken.
"""

from django.db import transaction
from slugify import slugify

from django_contentdb.models import AccessRights, Content, ContentChannel, ContentType, Draft, Language, Route
from django_contentdb.services import article_converter
from django_contentdb.services.content_service import sanitize_content
from django_contentdb.settings import ENRICHMENT_DOCUMENT_TYPE

PUBLIC_ACCESS_LEVEL = 1
ROUTE_MAX_LENGTH = 256


@transaction.atomic
def create_draft(value: dict, *, channel: str = "") -> Draft:
    """A new unpublished draft of the document content type, built from the document `value`."""
    content_type = _document_type()
    language = _language(value.get("language", ""))
    payload = article_converter.build_payload(_markdown(value), _converter_meta(value), slug="")
    content = Content.objects.create(
        content=sanitize_content(payload["content"]),
        meta=sanitize_content(payload["meta"]),
        extension=sanitize_content(payload["extension"]),
    )
    draft = Draft.objects.create(
        content_type=content_type, content=content, name=payload["name"][:128], language=language
    )
    draft.access_rights.set([AccessRights.objects.get_or_create(access_level=PUBLIC_ACCESS_LEVEL)[0]])
    draft.channels.set(ContentChannel.objects.filter(idx=channel) if channel else [])
    Route.objects.create(url=unique_route(value.get("slug") or payload["name"])).drafts.add(draft)
    return draft


@transaction.atomic
def delete_draft(draft: Draft) -> None:
    """Delete a draft that was never published (with routes only it uses); a published one raises `ValueError`."""
    if draft.published.exists():
        raise ValueError("the draft has been published; unpublish it in the CMS before undoing its creation")
    for route in draft.routes.all():
        if route.drafts.exclude(pk=draft.pk).exists():
            continue
        route.delete()
    draft.content.delete()


def unique_route(slug: str) -> str:
    base = slugify(slug)[: ROUTE_MAX_LENGTH - 8] or "article"
    route, suffix = base, 1
    while Route.objects.filter(url=route).exists():
        suffix += 1
        route = f"{base}-{suffix}"
    return route


def _document_type() -> ContentType:
    content_type = ContentType.objects.filter(slug=ENRICHMENT_DOCUMENT_TYPE).first()
    if content_type is None:
        raise ValueError(f"content type {ENRICHMENT_DOCUMENT_TYPE!r} does not exist")
    return content_type


def _language(iso2: str) -> Language:
    language = Language.objects.filter(iso2__iexact=iso2).first() if iso2 else None
    if language is None:
        raise ValueError(f"unknown document language {iso2!r}")
    return language


def _markdown(value: dict) -> str:
    """Title as H1, the body, then the `faq` list as a `## FAQ` block (unless the body already has one)."""
    parts = [f"# {value.get('title', '')}", value.get("body_markdown", "")]
    faq = value.get("faq") or []
    if faq and not _has_faq_heading(parts[1]):
        parts.append("## FAQ")
        parts.extend(f"### {item['question']}\n\n{item['answer']}" for item in faq)
    return "\n\n".join(parts)


def _has_faq_heading(markdown: str) -> bool:
    headings = (line[3:] for line in markdown.splitlines() if line.startswith("## "))
    return any(article_converter.FAQ_HEADING.search(heading) for heading in headings)


def _converter_meta(value: dict) -> dict:
    meta = value.get("meta") or {}
    return {
        "lang": value.get("language", "en"),
        "title": value.get("title", ""),
        "seo_title": meta.get("title", ""),
        "seo_description": meta.get("description", ""),
        "og_title": meta.get("og_title", ""),
        "og_description": meta.get("og_description", ""),
    }
