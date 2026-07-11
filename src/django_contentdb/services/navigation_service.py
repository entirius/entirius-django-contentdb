# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.core.cache import cache
from django.db.models import Max, Q

from django_contentdb.models import Content, Published
from django_contentdb.schemas.navigation import NavigationContent

CACHE_KEY_PREFIX = "contentdb:nav"
CACHE_TTL = getattr(settings, "CONTENTDB_NAVIGATION_CACHE_TTL", 300)


def validate_navigation_content(content_json: dict) -> NavigationContent:
    return NavigationContent(**content_json)


def get_published_navigation(
    content_type_slug: str,
    language_iso2: str | None = None,
    channel_idx: str | None = None,
) -> dict | None:
    cache_key = f"{CACHE_KEY_PREFIX}:{content_type_slug}:{channel_idx}:{language_iso2}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    qs = Published.objects.select_related("draft__content_type", "draft__language", "content").filter(
        draft__content_type__slug=content_type_slug,
        draft__content_type__is_layout_extender=True,
    )
    if language_iso2:
        qs = qs.filter(draft__language__iso2__iexact=language_iso2)
    if channel_idx:
        qs = qs.filter(Q(draft__channels__idx=channel_idx) | Q(draft__channels__isnull=True))

    published = qs.order_by("-created_at").first()
    if not published:
        return None

    result = {
        "uid": str(published.content.uid),
        "name": published.draft.name,
        "content": published.content.content,
        "language": published.draft.language.iso2 if published.draft.language else "",
        "published_at": published.created_at.isoformat(),
    }
    cache.set(cache_key, result, CACHE_TTL)
    return result


def invalidate_navigation_cache(content_type_slug: str) -> None:
    try:
        cache.delete_pattern(f"{CACHE_KEY_PREFIX}:{content_type_slug}:*")
    except (AttributeError, NotImplementedError):
        pass


def get_published_siblings(
    *,
    content_uid: str,
    content_type_slug: str,
    channel_idx: str | None = None,
    language_iso2: str | None = None,
) -> dict:
    """Return ``{"prev": {...} | None, "next": {...} | None}`` for a published article.

    ``prev`` = older (earlier ``draft.created_at``); ``next`` = newer.
    Scope: same ``content_type``, channel (or ``channels=null``), language (if provided).
    Dedup per ``draft_id`` — only the latest published Content per Draft is considered
    (mirror of ``ROPublishedViewSet.get_queryset`` in ``views/public/published.py``).
    """
    base = Content.objects.filter(
        published__isnull=False,
        published__draft__content_type__slug=content_type_slug,
    )
    if language_iso2:
        base = base.filter(published__draft__language__iso2__iexact=language_iso2)
    if channel_idx:
        base = base.filter(Q(published__draft__channels__idx=channel_idx) | Q(published__draft__channels__isnull=True))

    latest_ids = base.values("published__draft").annotate(latest_id=Max("id")).values_list("latest_id", flat=True)
    qs = (
        Content.objects.filter(id__in=latest_ids)
        .select_related("published__draft__content_type", "published__draft__language")
        .prefetch_related("published__draft__routes")
    )

    current = qs.filter(uid=content_uid).first()
    if not current:
        return {"prev": None, "next": None}

    anchor = current.published.draft.created_at
    prev_content = (
        qs.filter(published__draft__created_at__lt=anchor).order_by("-published__draft__created_at", "-id").first()
    )
    next_content = (
        qs.filter(published__draft__created_at__gt=anchor).order_by("published__draft__created_at", "id").first()
    )
    return {
        "prev": _serialize_sibling(prev_content),
        "next": _serialize_sibling(next_content),
    }


def _serialize_sibling(content: Content | None) -> dict | None:
    if content is None:
        return None
    draft = content.published.draft
    extension = content.extension if isinstance(content.extension, dict) else {}
    return {
        "uid": str(content.uid),
        "name": draft.name,
        "title": extension.get("title"),
        "routes": [r.url for r in draft.routes.all()],
    }
