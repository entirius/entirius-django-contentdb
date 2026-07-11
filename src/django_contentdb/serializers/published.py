# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers
from rest_framework.relations import SlugRelatedField

from django_contentdb.models import Content, Draft, Published
from django_contentdb.serializers import ContentSerializer
from django_contentdb.serializers.fields import (
    AuthorBriefField,
    CoAuthorBriefField,
    ContentSetField,
    PublishedContentSetMembersField,
)


class PublishedContentSerializer(ContentSerializer):
    def create(self, validated_data):
        draft_uid = self.context["draft_uid"]
        draft = Draft.objects.get(content__uid=draft_uid)
        instance = super().create(validated_data)
        link = Published.objects.create(content=instance, draft=draft)
        return instance

    created_at = serializers.DateTimeField(source="published.draft.created_at", read_only=True)
    access_rights = SlugRelatedField(
        source="published.draft.access_rights", many=True, slug_field="access_level", read_only=True, required=False
    )
    channels = SlugRelatedField(source="published.draft.channels", many=True, slug_field="idx", read_only=True)
    language = SlugRelatedField(source="published.draft.language", read_only=True, slug_field="iso2")
    content_set = ContentSetField(source="published.draft", read_only=True)
    content_set_members = PublishedContentSetMembersField(source="published.draft", read_only=True)
    content_type = SlugRelatedField(source="published.draft.content_type", read_only=True, slug_field="slug")
    name = SlugRelatedField(source="published.draft", read_only=True, slug_field="name")
    routes = SlugRelatedField(read_only=True, source="published.draft.routes", many=True, slug_field="url")
    authors = AuthorBriefField(source="published.draft", read_only=True)
    co_authors = CoAuthorBriefField(source="published.draft", read_only=True)
    prev = serializers.SerializerMethodField()
    next = serializers.SerializerMethodField()

    class Meta:
        model = Content
        fields = [
            "uid",
            "content",
            "category",
            "meta",
            "attributes",
            "has_extension",
            "extension",
            "created_at",
            "updated_at",
            "content_set",
            "content_set_members",
            "content_type",
            "language",
            "name",
            "routes",
            "access_rights",
            "channels",
            "authors",
            "co_authors",
            "prev",
            "next",
        ]

    def get_prev(self, obj) -> dict | None:
        return self.context.get("siblings", {}).get("prev")

    def get_next(self, obj) -> dict | None:
        return self.context.get("siblings", {}).get("next")
