# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Tests for the navigation megamenu feature in django-contentdb.

Covers:
- Pydantic schema validation (NavigationContent, NavigationItem, NavigationColumn, NavigationLink)
- v2 Public API: GET /api/contentdb/v2/navigation/{content_type_slug}/
- Content.delete() protection via is_system flag on Draft
- Footer ContentType (is_layout_extender=True)
- NavigationService helper functions

URL (from api/v2/urls.py):
    GET /api/contentdb/v2/navigation/<str:content_type_slug>/

Test settings use:
    DEFAULT_PERMISSION_CLASSES = ["rest_framework.permissions.AllowAny"]
    DEFAULT_AUTHENTICATION_CLASSES = []

AllowAny is the real production permission on the navigation endpoint, so test
settings match production behaviour for this endpoint.
"""

import pytest
from pydantic import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.test import APIClient

from django_contentdb.models import AttributeSet, Content, ContentType, Draft, Language, Published, Route

NAVIGATION_URL = "/api/contentdb/v2/navigation/"


# ---------------------------------------------------------------------------
# Inline factory helpers
# ---------------------------------------------------------------------------


def make_attr_set(label="Test Attrs"):
    return AttributeSet.objects.create(label=label)


def make_content_type(attr_set=None, slug="header", is_layout_extender=True, **kwargs):
    if attr_set is None:
        attr_set = make_attr_set(f"Set-{slug}")
    return ContentType.objects.get_or_create(
        slug=slug,
        defaults={"label": slug, "attribute_set": attr_set, "is_layout_extender": is_layout_extender, **kwargs},
    )[0]


def make_language(iso2="en", iso3="eng"):
    return Language.objects.get_or_create(iso2=iso2, defaults={"iso3": iso3})[0]


def make_content(content_json=None):
    return Content.objects.create(content=content_json or {})


def make_draft(content_type, content, language, name="Test Nav", is_system=False):
    return Draft.objects.create(
        content_type=content_type,
        content=content,
        language=language,
        name=name,
        is_system=is_system,
    )


def make_published(draft, content=None):
    pub_content = content if content is not None else Content.objects.create()
    return Published.objects.create(draft=draft, content=pub_content)


# ---------------------------------------------------------------------------
# Sample navigation JSON payloads
# ---------------------------------------------------------------------------

SIMPLE_NAV_JSON = {
    "items": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440020",
            "label": "FURNITURE",
            "display_as": "link",
            "link_type": "category",
            "link_value": "furniture",
            "sort_order": 0,
            "columns": [],
        }
    ]
}

MEGAMENU_NAV_JSON = {
    "items": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440020",
            "label": "FURNITURE",
            "display_as": "megamenu",
            "link_type": "category",
            "link_value": "furniture",
            "sort_order": 0,
            "columns": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440010",
                    "type": "links",
                    "heading": "Shop by Category",
                    "sort_order": 0,
                    "links": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440001",
                            "label": "Best sellers",
                            "link_type": "category",
                            "link_value": "sofas",
                            "sort_order": 0,
                        }
                    ],
                }
            ],
        }
    ]
}


# ---------------------------------------------------------------------------
# TestNavigationSchema
# ---------------------------------------------------------------------------


class TestNavigationSchema:
    def test_valid_navigation_content(self):
        from django_contentdb.schemas.navigation import NavigationContent

        schema = NavigationContent(items=[])

        assert schema.items == []

    def test_valid_megamenu_item(self):
        from django_contentdb.schemas.navigation import NavigationContent

        schema = NavigationContent(**MEGAMENU_NAV_JSON)

        assert len(schema.items) == 1
        item = schema.items[0]
        assert item.label == "FURNITURE"
        assert item.display_as == "megamenu"
        assert len(item.columns) == 1
        assert item.columns[0].heading == "Shop by Category"
        assert len(item.columns[0].links) == 1
        assert item.columns[0].links[0].label == "Best sellers"

    def test_valid_simple_link(self):
        from django_contentdb.schemas.navigation import NavigationContent

        schema = NavigationContent(**SIMPLE_NAV_JSON)

        assert len(schema.items) == 1
        item = schema.items[0]
        assert item.display_as == "link"
        assert item.columns == []

    def test_invalid_display_as(self):
        from django_contentdb.schemas.navigation import NavigationItem

        with pytest.raises(ValidationError):
            NavigationItem(
                id="abc",
                label="Nav",
                display_as="dropdown",
                link_type="url",
            )

    def test_invalid_link_type(self):
        from django_contentdb.schemas.navigation import NavigationItem

        with pytest.raises(ValidationError):
            NavigationItem(
                id="abc",
                label="Nav",
                display_as="link",
                link_type="external",
            )

    def test_max_columns_exceeded(self):
        from django_contentdb.schemas.navigation import NavigationColumn, NavigationItem

        columns = [NavigationColumn(id=f"col-{i}", type="links", sort_order=i) for i in range(5)]

        with pytest.raises(ValidationError, match="more than 4 columns"):
            NavigationItem(
                id="abc",
                label="Nav",
                display_as="megamenu",
                link_type="category",
                columns=columns,
            )

    def test_max_columns_ok_for_link(self):
        """Link items do not validate column count — columns are ignored for display_as=link."""
        from django_contentdb.schemas.navigation import NavigationColumn, NavigationItem

        columns = [NavigationColumn(id=f"col-{i}", type="links", sort_order=i) for i in range(5)]

        # link items have no column limit enforced by the validator
        item = NavigationItem(
            id="abc",
            label="Nav",
            display_as="link",
            link_type="url",
            link_value="https://example.com",
            columns=columns,
        )

        assert len(item.columns) == 5


# ---------------------------------------------------------------------------
# TestNavigationPublicAPI
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNavigationPublicAPI:
    def test_get_published_navigation_200(self):
        lang = make_language()
        ct = make_content_type(slug="header", is_layout_extender=True)
        content = make_content(SIMPLE_NAV_JSON)
        draft = make_draft(ct, content, lang, name="Main Header")
        make_published(draft)
        client = APIClient()

        response = client.get(f"{NAVIGATION_URL}header/")

        assert response.status_code == 200

    def test_get_navigation_404_no_published(self):
        lang = make_language()
        ct = make_content_type(slug="header-draft-only", is_layout_extender=True)
        content = make_content(SIMPLE_NAV_JSON)
        make_draft(ct, content, lang, name="Unpublished")
        client = APIClient()

        response = client.get(f"{NAVIGATION_URL}header-draft-only/")

        assert response.status_code == 404

    def test_get_navigation_404_nonexistent_type(self):
        client = APIClient()

        response = client.get(f"{NAVIGATION_URL}does-not-exist/")

        assert response.status_code == 404

    def test_response_shape(self):
        lang = make_language()
        ct = make_content_type(slug="header-shape", is_layout_extender=True)
        content = make_content(SIMPLE_NAV_JSON)
        draft = make_draft(ct, content, lang, name="Shape Test Nav")
        make_published(draft)
        client = APIClient()

        response = client.get(f"{NAVIGATION_URL}header-shape/")

        assert response.status_code == 200
        for field in ("uid", "name", "content", "language", "published_at"):
            assert field in response.data, f"Missing field: {field}"

    def test_language_filter(self):
        lang_en = make_language(iso2="en", iso3="eng")
        lang_pl = make_language(iso2="pl", iso3="pol")
        ct = make_content_type(slug="header-lang", is_layout_extender=True)
        content_en = make_content(SIMPLE_NAV_JSON)
        content_pl = make_content(SIMPLE_NAV_JSON)
        draft_en = make_draft(ct, content_en, lang_en, name="EN Header")
        draft_pl = make_draft(ct, content_pl, lang_pl, name="PL Header")
        make_published(draft_en)
        make_published(draft_pl)
        client = APIClient()

        response = client.get(f"{NAVIGATION_URL}header-lang/", {"language": "pl"})

        assert response.status_code == 200
        assert response.data["language"] == "pl"
        assert response.data["name"] == "PL Header"

    def test_no_auth_required(self):
        lang = make_language()
        ct = make_content_type(slug="header-anon", is_layout_extender=True)
        content = make_content(SIMPLE_NAV_JSON)
        draft = make_draft(ct, content, lang)
        make_published(draft)
        client = APIClient()  # no authentication

        response = client.get(f"{NAVIGATION_URL}header-anon/")

        assert response.status_code == 200

    def test_content_contains_items(self):
        lang = make_language()
        ct = make_content_type(slug="header-items", is_layout_extender=True)
        content = make_content(MEGAMENU_NAV_JSON)
        draft = make_draft(ct, content, lang, name="Megamenu Nav")
        pub_content = make_content(MEGAMENU_NAV_JSON)
        make_published(draft, content=pub_content)
        client = APIClient()

        response = client.get(f"{NAVIGATION_URL}header-items/")

        assert response.status_code == 200
        assert "items" in response.data["content"]
        assert len(response.data["content"]["items"]) == 1

    def test_navigation_404_for_regular_content_type(self):
        lang = make_language()
        ct = make_content_type(slug="static-page-nav-check", is_layout_extender=False)
        content = make_content(SIMPLE_NAV_JSON)
        draft = make_draft(ct, content, lang)
        make_published(draft)
        client = APIClient()

        # The service filters on is_layout_extender=True, so non-extender types return 404
        response = client.get(f"{NAVIGATION_URL}static-page-nav-check/")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestIsSystemProtection
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIsSystemProtection:
    def test_system_content_cannot_be_deleted(self):
        lang = make_language()
        ct = make_content_type(slug="sys-ct", is_layout_extender=True)
        content = make_content()
        make_draft(ct, content, lang, is_system=True)

        with pytest.raises(DRFValidationError, match="Cannot delete system content"):
            content.delete()

    def test_system_content_can_be_deleted_with_bypass(self):
        lang = make_language()
        ct = make_content_type(slug="sys-bypass-ct", is_layout_extender=True)
        content = make_content()
        make_draft(ct, content, lang, is_system=True)
        content_pk = content.pk

        content.delete(bypass=True)

        assert not Content.objects.filter(pk=content_pk).exists()

    def test_non_system_content_can_be_deleted(self):
        lang = make_language()
        ct = make_content_type(slug="non-sys-ct", is_layout_extender=True)
        content = make_content()
        make_draft(ct, content, lang, is_system=False)
        content_pk = content.pk

        content.delete()

        assert not Content.objects.filter(pk=content_pk).exists()

    def test_system_draft_allows_content_update(self):
        lang = make_language()
        ct = make_content_type(slug="sys-update-ct", is_layout_extender=True)
        content = make_content({"items": []})
        make_draft(ct, content, lang, is_system=True)

        # Updating the JSON content should not raise
        content.content = SIMPLE_NAV_JSON
        content.save()
        content.refresh_from_db()

        assert content.content == SIMPLE_NAV_JSON


# ---------------------------------------------------------------------------
# TestFooterContentType
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFooterContentType:
    def test_footer_content_type_exists(self):
        ct = make_content_type(slug="footer", is_layout_extender=True)

        assert ct.slug == "footer"
        assert ct.is_layout_extender is True

    def test_footer_not_published_returns_404(self):
        make_content_type(slug="footer-404", is_layout_extender=True)
        client = APIClient()

        response = client.get(f"{NAVIGATION_URL}footer-404/")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestNavigationService
# ---------------------------------------------------------------------------


class TestNavigationService:
    def test_validate_navigation_content_valid(self):
        from django_contentdb.services import navigation_service

        result = navigation_service.validate_navigation_content(MEGAMENU_NAV_JSON)

        assert result is not None
        assert len(result.items) == 1
        assert result.items[0].label == "FURNITURE"

    def test_validate_navigation_content_invalid(self):
        from django_contentdb.services import navigation_service

        with pytest.raises(ValidationError):
            navigation_service.validate_navigation_content(
                {"items": [{"id": "x", "label": "Bad", "display_as": "not-valid", "link_type": "url"}]}
            )

    def test_invalidate_cache_does_not_raise(self):
        from django_contentdb.services import navigation_service

        # Should handle missing cache backend (AttributeError / NotImplementedError) gracefully
        navigation_service.invalidate_navigation_cache("header")


# ---------------------------------------------------------------------------
# TestProtectedRouteDeletion
# ---------------------------------------------------------------------------


def _make_route(url):
    return Route.objects.create(url=url)


def _make_draft_with_route(slug, route_url, lang):
    ct = make_content_type(slug=slug, is_layout_extender=False)
    content = make_content()
    draft = make_draft(ct, content, lang, name=f"draft-{slug}")
    route = _make_route(route_url)
    route.drafts.add(draft)
    return draft, content


@pytest.mark.django_db
class TestProtectedRouteDeletion:
    def test_delete_last_home_draft_blocked(self):
        lang = make_language()
        _, content = _make_draft_with_route("home-only", "home", lang)

        with pytest.raises(DRFValidationError, match="Cannot delete the last home page"):
            content.delete()

    def test_delete_duplicate_home_draft_allowed(self):
        lang = make_language()
        _, content_a = _make_draft_with_route("home-a", "home", lang)
        # share the same Route so both drafts point to url="home"
        route_home = Route.objects.get(url="home")
        ct_b = make_content_type(slug="home-b", is_layout_extender=False)
        content_b = make_content()
        draft_b = make_draft(ct_b, content_b, lang, name="draft-home-b")
        route_home.drafts.add(draft_b)

        content_a.delete()

        assert not Content.objects.filter(pk=content_a.pk).exists()
        assert Draft.objects.filter(routes__url="home").count() == 1

    def test_delete_last_header_draft_blocked(self):
        lang = make_language()
        _, content = _make_draft_with_route("header-only", "header", lang)

        with pytest.raises(DRFValidationError, match="Cannot delete the last header page"):
            content.delete()

    def test_delete_duplicate_header_draft_allowed(self):
        lang = make_language()
        _, content_a = _make_draft_with_route("header-a", "header", lang)
        route_header = Route.objects.get(url="header")
        ct_b = make_content_type(slug="header-b", is_layout_extender=False)
        content_b = make_content()
        draft_b = make_draft(ct_b, content_b, lang, name="draft-header-b")
        route_header.drafts.add(draft_b)

        content_a.delete()

        assert not Content.objects.filter(pk=content_a.pk).exists()
        assert Draft.objects.filter(routes__url="header").count() == 1

    def test_delete_content_without_draft_allowed(self):
        content = make_content()
        content_pk = content.pk

        content.delete()

        assert not Content.objects.filter(pk=content_pk).exists()

    def test_delete_last_home_draft_bypass_allowed(self):
        lang = make_language()
        _, content = _make_draft_with_route("home-bypass", "home", lang)
        content_pk = content.pk

        content.delete(bypass=True)

        assert not Content.objects.filter(pk=content_pk).exists()

    def test_route_home_delete_raises_validation_error(self):
        route = _make_route("home")
        with pytest.raises(DRFValidationError, match="Cannot delete home route"):
            route.delete()

    def test_route_header_delete_raises_validation_error(self):
        route = _make_route("header")
        with pytest.raises(DRFValidationError, match="Cannot delete header route"):
            route.delete()

    def test_route_regular_delete_allowed(self):
        route = _make_route("about")
        route_pk = route.pk

        route.delete()

        assert not Route.objects.filter(pk=route_pk).exists()
