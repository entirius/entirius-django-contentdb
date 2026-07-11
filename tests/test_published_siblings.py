# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Tests for blog-post prev/next siblings on the public published endpoint.

Covers:
- Sibling resolution by published__draft__created_at (prev=older, next=newer)
- Boundary cases (first/last/only article)
- Language and channel scoping
- distinct-per-draft dedup
- List endpoint returns prev/next as null (API contract: fields always declared)

URL:
    GET /api/contentdb/v1/published/blog-post/<uid>/
    GET /api/contentdb/v1/published/blog-post/?language=&channel=

Test settings use AllowAny which matches production for this endpoint.
"""

import datetime as dt

import pytest
from rest_framework.test import APIClient

from django_contentdb.models import (
    AttributeSet,
    Content,
    ContentChannel,
    ContentType,
    Draft,
    Language,
    Published,
    Route,
)
from django_contentdb.services import navigation_service

BASE = "/api/contentdb/v1/published/blog-post/"


# ---------------------------------------------------------------------------
# Inline factory helpers (mirror tests/test_navigation_api.py style)
# ---------------------------------------------------------------------------


def make_attr_set(label="Blog Attrs"):
    return AttributeSet.objects.create(label=label)


def make_blog_type(slug="blog-post"):
    attr_set = AttributeSet.objects.filter(label=f"Set-{slug}").first() or make_attr_set(f"Set-{slug}")
    return ContentType.objects.get_or_create(
        slug=slug,
        defaults={"label": slug, "attribute_set": attr_set, "is_layout_extender": False},
    )[0]


def make_language(iso2="en", iso3="eng"):
    return Language.objects.get_or_create(iso2=iso2, defaults={"iso3": iso3})[0]


def make_channel(idx="default-europe"):
    lang = make_language()
    return ContentChannel.objects.get_or_create(idx=idx, defaults={"name": idx.title(), "default_language": lang})[0]


def make_route(url, draft=None):
    route, _ = Route.objects.get_or_create(url=url)
    if draft is not None:
        route.drafts.add(draft)
    return route


def make_published_blog(
    *,
    slug,
    name,
    language=None,
    content_type=None,
    channels=None,
    created_at=None,
    route_url=None,
    extension=None,
):
    """Create a Content + Draft + Published triple matching the list endpoint shape.

    Re-publishing the same draft creates additional Content + Published — done via
    ``republish()`` below.
    """
    if language is None:
        language = make_language()
    if content_type is None:
        content_type = make_blog_type()
    draft_content = Content.objects.create(content={})
    draft = Draft.objects.create(content_type=content_type, content=draft_content, language=language, name=name)
    if channels:
        for ch in channels:
            draft.channels.add(ch)
    if created_at is not None:
        Draft.objects.filter(pk=draft.pk).update(created_at=created_at)
        draft.refresh_from_db()
    pub_content = Content.objects.create(content={"body": name}, extension=extension)
    Published.objects.create(draft=draft, content=pub_content)
    make_route(route_url or slug, draft=draft)
    return pub_content, draft


def republish(draft):
    """Create one more Published row pointing to a fresh Content snapshot for the same draft."""
    pub_content = Content.objects.create(content={"body": "snapshot"})
    Published.objects.create(draft=draft, content=pub_content)
    return pub_content


def _detail_url(uid):
    return f"{BASE}{uid}/"


# ---------------------------------------------------------------------------
# Service-level tests (faster, no HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetPublishedSiblingsService:
    def test_middle_article_has_both_neighbours(self):
        lang = make_language("en")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        older, _ = make_published_blog(slug="post-a", name="A", language=lang, created_at=t0)
        middle, _ = make_published_blog(slug="post-b", name="B", language=lang, created_at=t0 + dt.timedelta(days=1))
        newer, _ = make_published_blog(slug="post-c", name="C", language=lang, created_at=t0 + dt.timedelta(days=2))

        result = navigation_service.get_published_siblings(
            content_uid=str(middle.uid),
            content_type_slug="blog-post",
            channel_idx=None,
            language_iso2="en",
        )

        assert result["prev"] is not None
        assert result["prev"]["uid"] == str(older.uid)
        assert result["prev"]["name"] == "A"
        assert result["prev"]["routes"] == ["post-a"]
        assert result["next"] is not None
        assert result["next"]["uid"] == str(newer.uid)
        assert result["next"]["name"] == "C"
        assert result["next"]["routes"] == ["post-c"]

    def test_newest_article_has_no_next(self):
        lang = make_language("en")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        make_published_blog(slug="p-a", name="A", language=lang, created_at=t0)
        newest, _ = make_published_blog(slug="p-b", name="B", language=lang, created_at=t0 + dt.timedelta(days=1))

        result = navigation_service.get_published_siblings(
            content_uid=str(newest.uid),
            content_type_slug="blog-post",
            channel_idx=None,
            language_iso2="en",
        )

        assert result["prev"] is not None
        assert result["prev"]["name"] == "A"
        assert result["next"] is None

    def test_oldest_article_has_no_prev(self):
        lang = make_language("en")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        oldest, _ = make_published_blog(slug="p-a", name="A", language=lang, created_at=t0)
        make_published_blog(slug="p-b", name="B", language=lang, created_at=t0 + dt.timedelta(days=1))

        result = navigation_service.get_published_siblings(
            content_uid=str(oldest.uid),
            content_type_slug="blog-post",
            channel_idx=None,
            language_iso2="en",
        )

        assert result["prev"] is None
        assert result["next"] is not None
        assert result["next"]["name"] == "B"

    def test_only_article_returns_both_null(self):
        lang = make_language("en")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        only, _ = make_published_blog(slug="alone", name="Solo", language=lang, created_at=t0)

        result = navigation_service.get_published_siblings(
            content_uid=str(only.uid),
            content_type_slug="blog-post",
            channel_idx=None,
            language_iso2="en",
        )

        assert result == {"prev": None, "next": None}

    def test_other_content_types_are_invisible(self):
        """A static-page between two blog-posts must not appear as their sibling."""
        lang = make_language("en")
        static_type = ContentType.objects.create(
            slug="static-page",
            label="static-page",
            attribute_set=AttributeSet.objects.create(label="Set-static"),
            is_layout_extender=False,
        )
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        make_published_blog(slug="blog-a", name="Blog A", language=lang, created_at=t0)
        # static page right in the middle of the timeline — must be filtered out
        make_published_blog(
            slug="static-x",
            name="Static",
            language=lang,
            content_type=static_type,
            created_at=t0 + dt.timedelta(days=1),
        )
        blog_c, _ = make_published_blog(
            slug="blog-c", name="Blog C", language=lang, created_at=t0 + dt.timedelta(days=2)
        )

        result = navigation_service.get_published_siblings(
            content_uid=str(blog_c.uid),
            content_type_slug="blog-post",
            channel_idx=None,
            language_iso2="en",
        )

        assert result["prev"] is not None
        assert result["prev"]["name"] == "Blog A"
        assert result["next"] is None

    def test_language_scoping_excludes_other_languages(self):
        en = make_language("en", "eng")
        pl = make_language("pl", "pol")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        # EN post, older
        make_published_blog(slug="en-older", name="EN older", language=en, created_at=t0)
        # PL post, in between (should NOT be a sibling of EN posts)
        make_published_blog(slug="pl-between", name="PL between", language=pl, created_at=t0 + dt.timedelta(days=1))
        en_newer, _ = make_published_blog(
            slug="en-newer", name="EN newer", language=en, created_at=t0 + dt.timedelta(days=2)
        )

        result = navigation_service.get_published_siblings(
            content_uid=str(en_newer.uid),
            content_type_slug="blog-post",
            channel_idx=None,
            language_iso2="en",
        )

        assert result["prev"] is not None
        assert result["prev"]["name"] == "EN older"
        assert result["next"] is None

    def test_channel_scoping_includes_channel_and_global(self):
        lang = make_language("en")
        ch_eu = make_channel("default-europe")
        ch_us = make_channel("us")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        # global (no channels)
        global_post, _ = make_published_blog(slug="global", name="Global", language=lang, created_at=t0)
        # EU only
        eu_post, _ = make_published_blog(
            slug="eu", name="EU", language=lang, created_at=t0 + dt.timedelta(days=1), channels=[ch_eu]
        )
        # US only — must not appear in EU scope
        make_published_blog(slug="us", name="US", language=lang, created_at=t0 + dt.timedelta(days=2), channels=[ch_us])

        result = navigation_service.get_published_siblings(
            content_uid=str(eu_post.uid),
            content_type_slug="blog-post",
            channel_idx="default-europe",
            language_iso2="en",
        )

        assert result["prev"] is not None
        assert result["prev"]["name"] == "Global"
        assert result["next"] is None  # US is not visible to EU

    def test_sibling_includes_extension_title(self):
        """Sibling payload exposes content.extension.title so the storefront can render the real heading."""
        lang = make_language("en")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        older, _ = make_published_blog(
            slug="post-a",
            name="post-a-internal",
            language=lang,
            created_at=t0,
            extension={"title": "Integracje e-commerce: Klucz do efektywnego zarządzania"},
        )
        middle, _ = make_published_blog(slug="post-b", name="B", language=lang, created_at=t0 + dt.timedelta(days=1))

        result = navigation_service.get_published_siblings(
            content_uid=str(middle.uid),
            content_type_slug="blog-post",
            channel_idx=None,
            language_iso2="en",
        )

        assert result["prev"] is not None
        assert result["prev"]["uid"] == str(older.uid)
        assert result["prev"]["name"] == "post-a-internal"
        assert result["prev"]["title"] == "Integracje e-commerce: Klucz do efektywnego zarządzania"

    def test_sibling_title_is_null_when_extension_missing(self):
        """No extension → title=null (frontend falls back to name); field is always declared."""
        lang = make_language("en")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        make_published_blog(slug="p-a", name="A", language=lang, created_at=t0)
        newer, _ = make_published_blog(slug="p-b", name="B", language=lang, created_at=t0 + dt.timedelta(days=1))

        result = navigation_service.get_published_siblings(
            content_uid=str(newer.uid),
            content_type_slug="blog-post",
            channel_idx=None,
            language_iso2="en",
        )

        assert result["prev"] is not None
        assert "title" in result["prev"]
        assert result["prev"]["title"] is None

    def test_distinct_per_draft_id(self):
        """Re-publishing a draft creates multiple Published rows; sibling logic must not duplicate."""
        lang = make_language("en")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        older, older_draft = make_published_blog(slug="a", name="A", language=lang, created_at=t0)
        # Republish twice — A now has 3 Published rows
        republish(older_draft)
        latest_a_content = republish(older_draft)
        middle, _ = make_published_blog(slug="b", name="B", language=lang, created_at=t0 + dt.timedelta(days=1))

        result = navigation_service.get_published_siblings(
            content_uid=str(middle.uid),
            content_type_slug="blog-post",
            channel_idx=None,
            language_iso2="en",
        )

        # prev must point to the LATEST Content of draft A, not the original one
        assert result["prev"] is not None
        assert result["prev"]["uid"] == str(latest_a_content.uid)
        assert result["prev"]["name"] == "A"


# ---------------------------------------------------------------------------
# HTTP-level tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPublishedSiblingsAPI:
    def test_retrieve_returns_prev_next_in_response(self):
        lang = make_language("en")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        make_published_blog(slug="post-a", name="A", language=lang, created_at=t0)
        middle, _ = make_published_blog(slug="post-b", name="B", language=lang, created_at=t0 + dt.timedelta(days=1))
        make_published_blog(slug="post-c", name="C", language=lang, created_at=t0 + dt.timedelta(days=2))
        client = APIClient()

        response = client.get(_detail_url(middle.uid), {"language": "en"})

        assert response.status_code == 200
        data = response.data["data"]
        assert data["prev"] is not None
        assert data["prev"]["name"] == "A"
        assert data["prev"]["routes"] == ["post-a"]
        assert data["next"] is not None
        assert data["next"]["name"] == "C"
        assert data["next"]["routes"] == ["post-c"]

    def test_list_returns_prev_next_as_null(self):
        """API contract: fields always declared; in list mode siblings are not computed → null."""
        lang = make_language("en")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        make_published_blog(slug="post-a", name="A", language=lang, created_at=t0)
        make_published_blog(slug="post-b", name="B", language=lang, created_at=t0 + dt.timedelta(days=1))
        client = APIClient()

        response = client.get(BASE, {"language": "en"})

        assert response.status_code == 200
        results = response.data["data"]
        assert len(results) == 2
        for item in results:
            assert "prev" in item
            assert "next" in item
            assert item["prev"] is None
            assert item["next"] is None

    def test_retrieve_includes_extension_title_on_siblings(self):
        """End-to-end: extension.title from sibling Content surfaces in HTTP response."""
        lang = make_language("en")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        make_published_blog(
            slug="post-a",
            name="post-a-internal",
            language=lang,
            created_at=t0,
            extension={"title": "Real Title A"},
        )
        middle, _ = make_published_blog(slug="post-b", name="B", language=lang, created_at=t0 + dt.timedelta(days=1))
        make_published_blog(
            slug="post-c",
            name="post-c-internal",
            language=lang,
            created_at=t0 + dt.timedelta(days=2),
            extension={"title": "Real Title C"},
        )
        client = APIClient()

        response = client.get(_detail_url(middle.uid), {"language": "en"})

        assert response.status_code == 200
        data = response.data["data"]
        assert data["prev"]["title"] == "Real Title A"
        assert data["next"]["title"] == "Real Title C"

    def test_list_with_routes_filter_populates_siblings(self):
        """Storefront pattern: list?routes=slug returns single item with prev/next computed."""
        lang = make_language("en")
        t0 = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
        make_published_blog(slug="post-a", name="A", language=lang, created_at=t0)
        make_published_blog(slug="post-b", name="B", language=lang, created_at=t0 + dt.timedelta(days=1))
        make_published_blog(slug="post-c", name="C", language=lang, created_at=t0 + dt.timedelta(days=2))
        client = APIClient()

        response = client.get(BASE, {"routes": "post-b", "language": "en"})

        assert response.status_code == 200
        results = response.data["data"]
        assert len(results) == 1
        item = results[0]
        assert item["prev"] is not None
        assert item["prev"]["name"] == "A"
        assert item["next"] is not None
        assert item["next"]["name"] == "C"
