# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers

from django_contentdb.models import Author


class PublicAuthorSerializer(serializers.ModelSerializer):
    """Read-only serializer for public author endpoints. Only active authors are served."""

    photo_uid = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    published_post_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Author
        fields = [
            "uid",
            "name",
            "slug",
            "role_t9n",
            "description_t9n",
            "tag_t9n",
            "photo_uid",
            "photo_url",
            "contact_email",
            "contact_phone",
            "contact_url",
            "social_profiles",
            "published_post_count",
        ]

    def get_photo_uid(self, obj: Author) -> str | None:
        return str(obj.photo.uid) if obj.photo else None

    def get_photo_url(self, obj: Author) -> str | None:
        if not obj.photo or not obj.photo.image:
            return None
        url = obj.photo.image.url
        request = self.context.get("request")
        if request:
            url = request.build_absolute_uri(url)
        return url
