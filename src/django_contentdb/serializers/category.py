# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max
from rest_framework import serializers

from django_contentdb.filters import PublishedFilter
from django_contentdb.models import Category, Content, Language


class CategorySerializer(serializers.ModelSerializer):
    language = serializers.CharField()
    published_posts_count = serializers.SerializerMethodField()

    def get_published_posts_count(self, obj):
        access_rights = (
            self.context.get("request").query_params.get("access_rights", None) if self.context.get("request") else None
        )

        queryset = Content.objects.all()
        queryset = PublishedFilter(queryset=queryset).qs
        latest_contents = (
            queryset.filter(published__isnull=False)
            .values("published__draft")
            .annotate(latest_id=Max("id"), latest_created=Max("published__created_at"))
            .values_list("latest_id", flat=True)
        )
        result = queryset.filter(id__in=latest_contents).filter(category=obj).distinct("published__draft_id")

        if access_rights:
            access_levels = [int(level) for level in access_rights.split(",")]
            result = result.filter(published__draft__access_rights__access_level__in=access_levels)

        return result.distinct().count()

    class Meta:
        model = Category
        fields = ["uid", "name", "url_key", "language", "published_posts_count"]
        read_only_fields = ["uid"]

    def create(self, validated_data):
        language_iso2 = validated_data.pop("language")
        try:
            language_instance = Language.objects.get(iso2=language_iso2)
        except ObjectDoesNotExist:
            raise serializers.ValidationError({"language": "Invalid language ISO2 code."})
        validated_data["language"] = language_instance
        return Category.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if "language" in validated_data:
            language_iso2 = validated_data.pop("language")
            try:
                language_instance = Language.objects.get(iso2=language_iso2)
            except ObjectDoesNotExist:
                raise serializers.ValidationError({"language": "Invalid language ISO2 code."})
            instance.language = language_instance
        instance.name = validated_data.get("name", instance.name)
        instance.url_key = validated_data.get("url_key", instance.url_key)
        instance.save()
        return instance
