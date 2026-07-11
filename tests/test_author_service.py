# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from django_contentdb.models import (
    AttributeSet,
    Author,
    Content,
    ContentType,
    Draft,
    DraftAuthor,
    DraftCoAuthor,
    Language,
    Published,
)
from django_contentdb.services import author_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_attr_set(label="Test Set"):
    return AttributeSet.objects.create(label=label)


def make_content_type(slug="blog-post", label="Blog Post", supports_authors=True):
    attr_set = make_attr_set(f"Set-{slug}")
    return ContentType.objects.get_or_create(
        slug=slug, defaults={"label": label, "attribute_set": attr_set, "supports_authors": supports_authors}
    )[0]


def make_language(iso2="en", iso3="eng"):
    return Language.objects.get_or_create(iso2=iso2, defaults={"iso3": iso3})[0]


def make_draft(content_type=None, language=None):
    if content_type is None:
        content_type = make_content_type()
    if language is None:
        language = make_language()
    content = Content.objects.create()
    return Draft.objects.create(content_type=content_type, content=content, language=language)


def make_published(draft):
    pub_content = Content.objects.create()
    return Published.objects.create(draft=draft, content=pub_content)


def make_author(name="Test Author", is_active=True):
    return Author.objects.create(name=name, is_active=is_active)


# ---------------------------------------------------------------------------
# list_authors
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListAuthors:
    def test_returns_all_authors(self):
        make_author("Alice")
        make_author("Bob")

        result = list(author_service.list_authors())

        names = {a.name for a in result}
        assert "Alice" in names
        assert "Bob" in names

    def test_is_active_filter_true(self):
        make_author("Active Author", is_active=True)
        make_author("Inactive Author", is_active=False)

        result = list(author_service.list_authors(is_active=True))

        names = {a.name for a in result}
        assert "Active Author" in names
        assert "Inactive Author" not in names

    def test_is_active_filter_false(self):
        make_author("Active", is_active=True)
        make_author("Inactive", is_active=False)

        result = list(author_service.list_authors(is_active=False))

        names = {a.name for a in result}
        assert "Inactive" in names
        assert "Active" not in names

    def test_search_filters_by_name(self):
        make_author("Anna Kowalska")
        make_author("John Smith")

        result = list(author_service.list_authors(search="anna"))

        assert len(result) == 1
        assert result[0].name == "Anna Kowalska"

    def test_search_filters_by_slug(self):
        make_author("Marek Nowak")  # slug: marek-nowak
        make_author("Other Person")

        result = list(author_service.list_authors(search="marek-nowak"))

        assert len(result) == 1
        assert result[0].name == "Marek Nowak"

    def test_published_post_count_annotation_present(self):
        author = make_author("Annotated Author")

        result = author_service.list_authors().get(pk=author.pk)

        assert hasattr(result, "published_post_count")

    def test_published_post_count_zero_with_no_posts(self):
        author = make_author("No Posts")

        result = author_service.list_authors().get(pk=author.pk)

        assert result.published_post_count == 0

    def test_published_post_count_counts_authored_posts(self):
        author = make_author("Prolific Author")
        ct = make_content_type()
        draft = make_draft(content_type=ct)
        DraftAuthor.objects.create(draft=draft, author=author, position=0)
        make_published(draft)

        result = author_service.list_authors().get(pk=author.pk)

        assert result.published_post_count == 1

    def test_published_post_count_includes_co_authored_posts(self):
        author = make_author("Co-Author")
        ct = make_content_type()
        draft = make_draft(content_type=ct)
        DraftCoAuthor.objects.create(draft=draft, author=author, position=0)
        make_published(draft)

        result = author_service.list_authors().get(pk=author.pk)

        assert result.published_post_count == 1

    def test_published_post_count_sums_author_and_co_author(self):
        author = make_author("Multi-Role Author")
        ct = make_content_type()

        draft_as_author = make_draft(content_type=ct)
        DraftAuthor.objects.create(draft=draft_as_author, author=author, position=0)
        make_published(draft_as_author)

        draft_as_co = make_draft(content_type=ct)
        DraftCoAuthor.objects.create(draft=draft_as_co, author=author, position=0)
        make_published(draft_as_co)

        result = author_service.list_authors().get(pk=author.pk)

        assert result.published_post_count == 2


# ---------------------------------------------------------------------------
# create_author
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateAuthor:
    def test_create_author_happy_path(self):
        data = {"name": "New Author", "contact_email": "new@example.com"}

        author = author_service.create_author(data)

        assert author.pk is not None
        assert author.name == "New Author"
        assert author.contact_email == "new@example.com"

    def test_create_author_auto_generates_slug(self):
        author = author_service.create_author({"name": "Auto Slug Author"})

        assert author.slug == "auto-slug-author"

    def test_create_author_with_explicit_slug(self):
        author = author_service.create_author({"name": "Author", "slug": "custom-slug"})

        assert author.slug == "custom-slug"

    def test_create_author_duplicate_slug_auto_incremented(self):
        author_service.create_author({"name": "Duplicate Slug"})
        second = author_service.create_author({"name": "Duplicate Slug"})

        assert second.slug == "duplicate-slug-2"

    def test_create_author_is_active_defaults_true(self):
        author = author_service.create_author({"name": "Active Default"})

        assert author.is_active is True

    def test_create_author_with_is_active_false(self):
        author = author_service.create_author({"name": "Inactive", "is_active": False})

        assert author.is_active is False


# ---------------------------------------------------------------------------
# update_author
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUpdateAuthor:
    def test_update_name(self):
        author = make_author("Original Name")

        updated = author_service.update_author(author.uid, {"name": "Updated Name"})

        assert updated.name == "Updated Name"

    def test_update_slug(self):
        author = make_author("Slug Author")

        updated = author_service.update_author(author.uid, {"slug": "new-custom-slug"})

        assert updated.slug == "new-custom-slug"

    def test_partial_update_does_not_overwrite_unset_fields(self):
        author = make_author("Partial Update")

        updated = author_service.update_author(author.uid, {"contact_email": "partial@example.com"})

        assert updated.name == "Partial Update"
        assert updated.contact_email == "partial@example.com"


# ---------------------------------------------------------------------------
# delete_author
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDeleteAuthor:
    def test_delete_removes_author(self):
        author = make_author("To Delete")

        author_service.delete_author(author.uid)

        assert not Author.objects.filter(pk=author.pk).exists()

    def test_delete_with_reassign_moves_draft_author_links(self):
        author_to_delete = make_author("Delete Me")
        replacement = make_author("Replacement")
        ct = make_content_type()
        draft = make_draft(content_type=ct)
        DraftAuthor.objects.create(draft=draft, author=author_to_delete, position=0)

        author_service.delete_author(author_to_delete.uid, reassign_to=replacement.uid)

        assert DraftAuthor.objects.filter(draft=draft, author=replacement).exists()
        assert not Author.objects.filter(pk=author_to_delete.pk).exists()

    def test_delete_with_reassign_moves_draft_co_author_links(self):
        author_to_delete = make_author("Delete Co")
        replacement = make_author("Co Replacement")
        ct = make_content_type()
        draft = make_draft(content_type=ct)
        DraftCoAuthor.objects.create(draft=draft, author=author_to_delete, position=0)

        author_service.delete_author(author_to_delete.uid, reassign_to=replacement.uid)

        assert DraftCoAuthor.objects.filter(draft=draft, author=replacement).exists()
        assert not Author.objects.filter(pk=author_to_delete.pk).exists()

    def test_delete_without_reassign_removes_draft_author_links(self):
        author = make_author("Orphan Author")
        ct = make_content_type()
        draft = make_draft(content_type=ct)
        DraftAuthor.objects.create(draft=draft, author=author, position=0)

        author_service.delete_author(author.uid, reassign_to=None)

        assert not DraftAuthor.objects.filter(draft=draft).exists()

    def test_delete_without_reassign_removes_draft_co_author_links(self):
        author = make_author("Orphan Co-Author")
        ct = make_content_type()
        draft = make_draft(content_type=ct)
        DraftCoAuthor.objects.create(draft=draft, author=author, position=0)

        author_service.delete_author(author.uid, reassign_to=None)

        assert not DraftCoAuthor.objects.filter(draft=draft).exists()

    def test_delete_nonexistent_raises(self):
        import uuid

        with pytest.raises(Author.DoesNotExist):
            author_service.delete_author(uuid.uuid4())


# ---------------------------------------------------------------------------
# set_draft_authors
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSetDraftAuthors:
    def test_set_draft_authors_creates_through_rows(self):
        ct = make_content_type()
        draft = make_draft(content_type=ct)
        a1 = make_author("A1")
        a2 = make_author("A2")

        author_service.set_draft_authors(draft, [a1.uid, a2.uid], [])

        assert DraftAuthor.objects.filter(draft=draft).count() == 2

    def test_set_draft_authors_assigns_positions(self):
        ct = make_content_type()
        draft = make_draft(content_type=ct)
        a1 = make_author("Pos First")
        a2 = make_author("Pos Second")

        author_service.set_draft_authors(draft, [a1.uid, a2.uid], [])

        positions = list(
            DraftAuthor.objects.filter(draft=draft).order_by("position").values_list("position", flat=True)
        )
        assert positions == [0, 1]

    def test_set_draft_authors_creates_co_author_rows(self):
        ct = make_content_type()
        draft = make_draft(content_type=ct)
        ca = make_author("Co-Author")

        author_service.set_draft_authors(draft, [], [ca.uid])

        assert DraftCoAuthor.objects.filter(draft=draft, author=ca).exists()

    def test_set_draft_authors_clears_previous_on_update(self):
        ct = make_content_type()
        draft = make_draft(content_type=ct)
        old = make_author("Old Author")
        new = make_author("New Author")
        DraftAuthor.objects.create(draft=draft, author=old, position=0)

        author_service.set_draft_authors(draft, [new.uid], [])

        assert not DraftAuthor.objects.filter(draft=draft, author=old).exists()
        assert DraftAuthor.objects.filter(draft=draft, author=new).exists()

    def test_set_draft_authors_clears_previous_co_authors(self):
        ct = make_content_type()
        draft = make_draft(content_type=ct)
        old_ca = make_author("Old Co")
        DraftCoAuthor.objects.create(draft=draft, author=old_ca, position=0)

        author_service.set_draft_authors(draft, [], [])

        assert not DraftCoAuthor.objects.filter(draft=draft).exists()

    def test_set_draft_authors_overlap_raises_value_error(self):
        ct = make_content_type()
        draft = make_draft(content_type=ct)
        shared = make_author("Shared Author")

        with pytest.raises(ValueError, match="author and co-author"):
            author_service.set_draft_authors(draft, [shared.uid], [shared.uid])
