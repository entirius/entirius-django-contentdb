# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers


class _AuthorBriefFieldBase(serializers.Field):
    """Serializes draft authors/co-authors as a list of brief dicts.
    Uses .all() to read from prefetch cache — do NOT call .select_related() here.
    """

    related_name: str = ""

    def to_representation(self, draft):
        request = self.context.get("request")
        manager = getattr(draft, self.related_name)
        result = []
        for link in manager.all():
            photo_url = None
            if link.author.photo and link.author.photo.image:
                photo_url = link.author.photo.image.url
                if request:
                    photo_url = request.build_absolute_uri(photo_url)
            result.append(
                {
                    "uid": str(link.author.uid),
                    "name": link.author.name,
                    "slug": link.author.slug,
                    "role_t9n": link.author.role_t9n,
                    "description_t9n": link.author.description_t9n,
                    "photo_uid": str(link.author.photo.uid) if link.author.photo else None,
                    "photo_url": photo_url,
                    "is_active": link.author.is_active,
                }
            )
        return result


class AuthorBriefField(_AuthorBriefFieldBase):
    related_name = "draft_authors"


class CoAuthorBriefField(_AuthorBriefFieldBase):
    related_name = "draft_co_authors"
