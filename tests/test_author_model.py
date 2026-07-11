# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from django.db import IntegrityError
from django.db.utils import IntegrityError as DjangoIntegrityError

from django_contentdb.models import (
    AttributeSet,
    Author,
    Content,
    ContentType,
    Draft,
    DraftAuthor,
    DraftCoAuthor,
    Language,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_attr_set(label="Test Set"):
    return AttributeSet.objects.create(label=label)


def make_content_type(slug="blog-post", label="Blog Post", supports_authors=True):
    attr_set = make_attr_set(f"Set {slug}")
    return ContentType.objects.create(slug=slug, label=label, attribute_set=attr_set, supports_authors=supports_authors)


def make_language(iso2="en", iso3="eng"):
    return Language.objects.get_or_create(iso2=iso2, defaults={"iso3": iso3})[0]


def make_draft(content_type=None, language=None):
    if content_type is None:
        content_type = make_content_type()
    if language is None:
        language = make_language()
    content = Content.objects.create()
    return Draft.objects.create(content_type=content_type, content=content, language=language)


# ---------------------------------------------------------------------------
# Author creation and basic fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAuthorCreation:
    def test_create_author_with_name(self):
        author = Author.objects.create(name="Anna Kowalska")

        assert author.pk is not None
        assert author.name == "Anna Kowalska"

    def test_is_active_defaults_true(self):
        author = Author.objects.create(name="Bob")

        assert author.is_active is True

    def test_json_fields_default_to_empty_dict(self):
        author = Author.objects.create(name="Carol")

        assert author.role_t9n == {}
        assert author.description_t9n == {}
        assert author.tag_t9n == {}
        assert author.social_profiles == {}

    def test_photo_defaults_null(self):
        author = Author.objects.create(name="Dan")

        assert author.photo is None

    def test_contact_fields_default_empty_string(self):
        author = Author.objects.create(name="Eve")

        assert author.contact_email == ""
        assert author.contact_phone == ""
        assert author.contact_url == ""

    def test_uid_auto_assigned(self):
        author = Author.objects.create(name="Frank")

        assert author.uid is not None

    def test_dunder_str_returns_name(self):
        author = Author.objects.create(name="Grace Hopper")

        assert str(author) == "Grace Hopper"


# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAuthorSlug:
    def test_slug_auto_generated_from_name(self):
        author = Author.objects.create(name="Anna Kowalska")

        assert author.slug == "anna-kowalska"

    def test_slug_normalised_on_save(self):
        author = Author.objects.create(name="Author", slug="UPPER--Case  Slug")

        assert author.slug == "upper-case-slug"

    def test_slug_collision_auto_increments(self):
        first = Author.objects.create(name="Anna Kowalska")
        second = Author.objects.create(name="Anna Kowalska")

        assert first.slug == "anna-kowalska"
        assert second.slug == "anna-kowalska-2"

    def test_third_collision_increments_to_three(self):
        Author.objects.create(name="Jan Nowak")
        Author.objects.create(name="Jan Nowak")
        third = Author.objects.create(name="Jan Nowak")

        assert third.slug == "jan-nowak-3"

    def test_explicit_slug_stored(self):
        author = Author.objects.create(name="Author X", slug="custom-slug")

        assert author.slug == "custom-slug"

    def test_slug_unique_constraint_raises_on_duplicate_direct(self):
        Author.objects.create(name="Unique One", slug="fixed-slug")

        with pytest.raises((IntegrityError, DjangoIntegrityError)):
            # Bypass save() via bulk_create to force a raw duplicate slug
            Author.objects.bulk_create([Author(name="Unique Two", slug="fixed-slug")])


# ---------------------------------------------------------------------------
# ContentType.supports_authors
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestContentTypeSupportsAuthors:
    def test_supports_authors_defaults_false(self):
        attr_set = make_attr_set("Default Set")
        ct = ContentType.objects.create(slug="static-page", label="Static Page", attribute_set=attr_set)

        assert ct.supports_authors is False

    def test_supports_authors_can_be_set_true(self):
        attr_set = make_attr_set("Blog Set")
        ct = ContentType.objects.create(
            slug="blog-post", label="Blog Post", attribute_set=attr_set, supports_authors=True
        )

        assert ct.supports_authors is True


# ---------------------------------------------------------------------------
# DraftAuthor through-table
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDraftAuthorThroughTable:
    def test_draft_author_creation(self):
        draft = make_draft()
        author = Author.objects.create(name="Author A")

        link = DraftAuthor.objects.create(draft=draft, author=author, position=0)

        assert link.pk is not None
        assert link.position == 0

    def test_draft_author_unique_constraint(self):
        draft = make_draft()
        author = Author.objects.create(name="Author B")
        DraftAuthor.objects.create(draft=draft, author=author, position=0)

        with pytest.raises((IntegrityError, DjangoIntegrityError)):
            DraftAuthor.objects.create(draft=draft, author=author, position=1)

    def test_draft_author_position_ordering(self):
        draft = make_draft()
        a1 = Author.objects.create(name="First")
        a2 = Author.objects.create(name="Second")
        DraftAuthor.objects.create(draft=draft, author=a2, position=1)
        DraftAuthor.objects.create(draft=draft, author=a1, position=0)

        positions = list(DraftAuthor.objects.filter(draft=draft).values_list("position", flat=True))
        assert positions == [0, 1]


# ---------------------------------------------------------------------------
# DraftCoAuthor through-table
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDraftCoAuthorThroughTable:
    def test_draft_co_author_creation(self):
        draft = make_draft()
        author = Author.objects.create(name="Co-Author A")

        link = DraftCoAuthor.objects.create(draft=draft, author=author, position=0)

        assert link.pk is not None

    def test_draft_co_author_unique_constraint(self):
        draft = make_draft()
        author = Author.objects.create(name="Co-Author B")
        DraftCoAuthor.objects.create(draft=draft, author=author, position=0)

        with pytest.raises((IntegrityError, DjangoIntegrityError)):
            DraftCoAuthor.objects.create(draft=draft, author=author, position=1)

    def test_draft_co_author_position_ordering(self):
        draft = make_draft()
        ca1 = Author.objects.create(name="Co First")
        ca2 = Author.objects.create(name="Co Second")
        DraftCoAuthor.objects.create(draft=draft, author=ca2, position=1)
        DraftCoAuthor.objects.create(draft=draft, author=ca1, position=0)

        positions = list(DraftCoAuthor.objects.filter(draft=draft).values_list("position", flat=True))
        assert positions == [0, 1]
