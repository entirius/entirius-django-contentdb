# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from uuid import UUID

from django.db.models import Count, OuterRef, Q, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce

from django_contentdb.models import Author, Draft, DraftAuthor, DraftCoAuthor, Image

BLOG_POST_SLUG = "blog-post"


def _post_count_subquery(through_model: type, channel_idx: str | None = None) -> Subquery:
    """Correlated subquery counting published blog posts for an author via a through table."""
    filters = Q(draft__content_type__slug=BLOG_POST_SLUG, draft__published__isnull=False)
    if channel_idx:
        filters &= Q(draft__channels__idx=channel_idx) | Q(draft__channels__isnull=True)

    return Subquery(
        through_model.objects.filter(author_id=OuterRef("pk"))
        .filter(filters)
        .order_by()
        .values("author_id")
        .annotate(cnt=Count("draft__published", distinct=True))
        .values("cnt")[:1]
    )


def _annotate_post_count(qs: QuerySet, channel_idx: str | None = None) -> QuerySet:
    """Annotate queryset with published_post_count (authors + co-authors combined).

    Uses two correlated subqueries instead of Count()+Count() in a single annotate()
    to avoid cartesian product from joining both DraftAuthor and DraftCoAuthor tables.
    """
    return qs.annotate(
        published_post_count=(
            Coalesce(_post_count_subquery(DraftAuthor, channel_idx), Value(0))
            + Coalesce(_post_count_subquery(DraftCoAuthor, channel_idx), Value(0))
        )
    )


def serialize_author(author: Author, request=None) -> dict:
    """Serialize an Author instance to a response dict. Used by v2 API views."""
    photo_url = None
    if author.photo and author.photo.image:
        photo_url = author.photo.image.url
        if request:
            photo_url = request.build_absolute_uri(photo_url)

    return {
        "uid": str(author.uid),
        "name": author.name,
        "slug": author.slug,
        "role_t9n": author.role_t9n,
        "description_t9n": author.description_t9n,
        "tag_t9n": author.tag_t9n,
        "photo_uid": str(author.photo.uid) if author.photo else None,
        "photo_url": photo_url,
        "contact_email": author.contact_email,
        "contact_phone": author.contact_phone,
        "contact_url": author.contact_url,
        "social_profiles": author.social_profiles,
        "is_active": author.is_active,
        "published_post_count": getattr(author, "published_post_count", 0),
    }


def list_authors(search: str | None = None, is_active: bool | None = None, channel_idx: str | None = None) -> QuerySet:
    qs = Author.objects.select_related("photo")

    if is_active is not None:
        qs = qs.filter(is_active=is_active)

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(slug__icontains=search))

    qs = _annotate_post_count(qs, channel_idx)
    return qs.order_by("-created_at")


def get_author(uid: str | UUID) -> Author:
    return Author.objects.select_related("photo").get(uid=uid)


def get_author_detail(uid: str | UUID, channel_idx: str | None = None) -> Author:
    """Single author with published_post_count annotation."""
    qs = Author.objects.select_related("photo").filter(uid=uid)
    qs = _annotate_post_count(qs, channel_idx)
    return qs.get()


def get_author_by_slug(slug: str, channel_idx: str | None = None) -> Author:
    """Single active author by slug with published_post_count annotation."""
    qs = Author.objects.select_related("photo").filter(slug=slug, is_active=True)
    qs = _annotate_post_count(qs, channel_idx)
    return qs.get()


def list_public_authors(channel_idx: str | None = None) -> QuerySet:
    """Active authors with at least one published post."""
    qs = Author.objects.select_related("photo").filter(is_active=True)
    qs = _annotate_post_count(qs, channel_idx)
    return qs.exclude(published_post_count=0).order_by("name")


def create_author(data: dict) -> Author:
    photo = None
    if photo_uid := data.pop("photo_uid", None):
        photo = Image.objects.get(uid=photo_uid)

    social = data.pop("social_profiles", None)
    if social is not None and hasattr(social, "model_dump"):
        social = social.model_dump(exclude_none=True)

    author = Author(
        name=data["name"],
        slug=data.get("slug") or "",
        role_t9n=data.get("role_t9n", {}),
        description_t9n=data.get("description_t9n", {}),
        tag_t9n=data.get("tag_t9n", {}),
        photo=photo,
        contact_email=data.get("contact_email", ""),
        contact_phone=data.get("contact_phone", ""),
        contact_url=data.get("contact_url", ""),
        social_profiles=social or {},
        is_active=data.get("is_active", True),
    )
    author.save()
    return author


def update_author(uid: str | UUID, data: dict) -> Author:
    author = Author.objects.select_related("photo").get(uid=uid)

    for field in (
        "name",
        "slug",
        "role_t9n",
        "description_t9n",
        "tag_t9n",
        "contact_email",
        "contact_phone",
        "contact_url",
        "is_active",
    ):
        if field in data and data[field] is not None:
            setattr(author, field, data[field])

    if "photo_uid" in data:
        if data["photo_uid"]:
            author.photo = Image.objects.get(uid=data["photo_uid"])
        else:
            author.photo = None

    if "social_profiles" in data and data["social_profiles"] is not None:
        social = data["social_profiles"]
        if hasattr(social, "model_dump"):
            social = social.model_dump(exclude_none=True)
        author.social_profiles = social

    author.save()
    return author


def delete_author(uid: str | UUID, reassign_to: str | UUID | None = None) -> None:
    author = Author.objects.get(uid=uid)

    if reassign_to:
        new_author = Author.objects.get(uid=reassign_to)

        # Remove rows where new_author already exists on the same draft to avoid UniqueConstraint violation
        existing_author_drafts = DraftAuthor.objects.filter(author=new_author).values_list("draft_id", flat=True)
        DraftAuthor.objects.filter(author=author, draft_id__in=existing_author_drafts).delete()
        DraftAuthor.objects.filter(author=author).update(author=new_author)

        existing_coauthor_drafts = DraftCoAuthor.objects.filter(author=new_author).values_list("draft_id", flat=True)
        DraftCoAuthor.objects.filter(author=author, draft_id__in=existing_coauthor_drafts).delete()
        DraftCoAuthor.objects.filter(author=author).update(author=new_author)
    else:
        DraftAuthor.objects.filter(author=author).delete()
        DraftCoAuthor.objects.filter(author=author).delete()

    author.delete()


def set_draft_authors(draft: Draft, author_uids: list[str | UUID], co_author_uids: list[str | UUID]) -> None:
    overlap = {str(u) for u in author_uids} & {str(u) for u in co_author_uids}
    if overlap:
        raise ValueError("An author cannot be both author and co-author on the same draft")

    DraftAuthor.objects.filter(draft=draft).delete()
    DraftCoAuthor.objects.filter(draft=draft).delete()

    all_uids = list(author_uids) + list(co_author_uids)
    if not all_uids:
        return

    authors_by_uid = {str(a.uid): a for a in Author.objects.filter(uid__in=all_uids)}

    missing = [str(u) for u in all_uids if str(u) not in authors_by_uid]
    if missing:
        raise ValueError(f"Author(s) not found: {', '.join(missing)}")

    DraftAuthor.objects.bulk_create(
        [DraftAuthor(draft=draft, author=authors_by_uid[str(uid)], position=pos) for pos, uid in enumerate(author_uids)]
    )
    DraftCoAuthor.objects.bulk_create(
        [
            DraftCoAuthor(draft=draft, author=authors_by_uid[str(uid)], position=pos)
            for pos, uid in enumerate(co_author_uids)
        ]
    )
