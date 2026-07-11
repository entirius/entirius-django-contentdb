# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import ValidationError

from django_contentdb.models import AccessRights, Content, ContentChannel, Draft, Language, Route
from django_contentdb.serializers import ContentSerializer
from django_contentdb.serializers.fields import (
    AuthorBriefField,
    CoAuthorBriefField,
    ContentSetField,
    CreateableSlugRelatedField,
    DraftContentSetMembersField,
)


class DraftContentSerializer(ContentSerializer):
    class IsPublishedField(serializers.Field):
        def to_representation(self, instance):
            return instance.published.exists()

    class IsUpToDateField(serializers.Field):
        def to_representation(self, instance):
            try:
                draft_content = instance.content.content
                latest_published_content = instance.published.last().content.content
                return str(draft_content) == str(latest_published_content)
            except Exception:
                return False

    def validate(self, attrs):
        _type = self.context.get("_type")
        if _type is None:
            raise ValidationError("Content must have a type")
        return super().validate(attrs)

    def create(self, validated_data):
        ModelCls = self.Meta.model
        # get ContentType instance from serializer context
        content_type = self.context["_type"]

        access_rights_levels = validated_data.get("draft", {}).get("access_rights", None)

        # Category
        category = validated_data.get("category", None)

        # Create Content instance
        instance = ModelCls.objects.create(
            content=validated_data["content"],
            extension=validated_data["extension"],
            meta=validated_data["meta"],
            category=category,
        )
        instance.attributes.add(*validated_data["attributes"])

        # Create Draft instance
        name = validated_data["draft"]["name"]
        language = validated_data["draft"]["language"]
        if validated_data["draft"]["language"] is not None:
            instance_draft = Draft.objects.create(
                content_type=content_type, content=instance, name=name, language=language
            )
        else:
            instance_draft = Draft.objects.create(content_type=content_type, content=instance, name=name)
        access_rights_objects = []
        if access_rights_levels is not None:
            for level in access_rights_levels:
                access_rights, is_created = AccessRights.objects.get_or_create(access_level=str(level))
                access_rights_objects.append(access_rights)
        instance_draft.access_rights.set(access_rights_objects)
        instance_draft.routes.add(*validated_data["draft"]["routes"])

        channel_idxs = validated_data.get("draft", {}).get("channels", None)
        if channel_idxs is not None:
            instance_draft.channels.set(channel_idxs)

        author_uids = validated_data.get("draft", {}).get("author_uids", None)
        co_author_uids = validated_data.get("draft", {}).get("co_author_uids", None)
        if author_uids is not None or co_author_uids is not None:
            from django_contentdb.services.author_service import set_draft_authors

            set_draft_authors(instance_draft, author_uids or [], co_author_uids or [])

        return instance

    def update(self, instance, validated_data):
        instance.content = validated_data["content"]
        instance.meta = validated_data["meta"]
        instance.extension = validated_data["extension"]

        # Category
        category = validated_data.get("category", None)
        instance.category = category

        access_rights_levels = validated_data.get("draft", {}).get("access_rights", None)
        instance.save()
        instance.attributes.clear()
        instance.attributes.add(*validated_data["attributes"])
        instance.draft.name = validated_data["draft"]["name"]
        if validated_data["draft"]["language"] is not None:
            instance.draft.language = validated_data["draft"]["language"]
        instance.draft.routes.clear()
        instance.draft.routes.add(*validated_data["draft"]["routes"])
        access_rights_objects = []
        if access_rights_levels is not None:
            for level in access_rights_levels:
                access_rights, is_created = AccessRights.objects.get_or_create(access_level=str(level))
                access_rights_objects.append(access_rights)
        instance.draft.access_rights.set(access_rights_objects)

        channel_idxs = validated_data.get("draft", {}).get("channels", None)
        if channel_idxs is not None:
            instance.draft.channels.set(channel_idxs)

        author_uids = validated_data.get("draft", {}).get("author_uids", None)
        co_author_uids = validated_data.get("draft", {}).get("co_author_uids", None)
        if author_uids is not None or co_author_uids is not None:
            from django_contentdb.services.author_service import set_draft_authors

            set_draft_authors(instance.draft, author_uids or [], co_author_uids or [])

        instance.draft.save()
        return instance

    access_rights = CreateableSlugRelatedField(
        source="draft.access_rights",
        many=True,
        slug_field="access_level",
        queryset=AccessRights.objects.all(),
        required=False,
    )
    channels = SlugRelatedField(
        source="draft.channels", many=True, slug_field="idx", queryset=ContentChannel.objects.all(), required=False
    )
    language = SlugRelatedField(
        source="draft.language",
        slug_field="iso2",
        queryset=Language.objects.all(),
        required=False,
        default=None,
        allow_null=True,
    )
    content_set = ContentSetField(source="draft", read_only=True)
    content_set_members = DraftContentSetMembersField(source="draft", read_only=True)
    content_type = SlugRelatedField(source="draft.content_type", read_only=True, slug_field="slug")
    name = serializers.CharField(source="draft.name", default="")
    routes = CreateableSlugRelatedField(
        source="draft.routes", many=True, slug_field="url", queryset=Route.objects.all()
    )
    authors = AuthorBriefField(source="draft", read_only=True)
    co_authors = CoAuthorBriefField(source="draft", read_only=True)
    author_uids = serializers.ListField(
        child=serializers.UUIDField(), source="draft.author_uids", required=False, write_only=True
    )
    co_author_uids = serializers.ListField(
        child=serializers.UUIDField(), source="draft.co_author_uids", required=False, write_only=True
    )
    is_published = IsPublishedField(read_only=True, source="draft")
    is_up_to_date = IsUpToDateField(read_only=True, source="draft")
    is_system = serializers.BooleanField(read_only=True, source="draft.is_system")

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
            "author_uids",
            "co_author_uids",
            "is_published",
            "is_up_to_date",
            "is_system",
        ]
