# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers

from django_contentdb.models import Image, ImageTag
from django_contentdb.serializers.fields import ExtendedBase64ImageField
from django_contentdb.serializers.image_tag import ImageTagSerializer
from django_contentdb.tasks import optimize_image


class ImageSerializer(serializers.ModelSerializer):
    class SourceSetField(serializers.Field):
        def to_representation(self, value):
            image = Image.objects.get(uid=value)
            thumbs = image.thumbnails.all()
            request = self.context.get("request")
            result = []
            for elem in thumbs:
                url = elem.image.url
                if request:
                    url = request.build_absolute_uri(url)
                result.append({"source": url, "width": elem.width, "height": elem.height})
            return result

    image = ExtendedBase64ImageField(required=False, allow_null=True)
    tags = ImageTagSerializer(many=True, required=False)
    set = SourceSetField(read_only=True, source="uid")

    def create(self, validated_data):
        tags_data = validated_data.pop("tags", [])
        # HACK Using standard super().create(**validated_data) does not work
        # May investigate in the fututre
        instance = self.Meta.model.objects.create(**validated_data)
        tags = []
        for tag_data in tags_data:
            tag, _ = ImageTag.objects.get_or_create(**tag_data)
            tags.append(tag)
        if len(tags) > 0:
            instance.tags.add(*tags)
        optimize_image(instance.pk)
        return instance

    def update(self, instance, validated_data):
        # Only update tags if they are provided in the request
        if "tags" in validated_data:
            instance.tags.clear()
            tags_data = validated_data.pop("tags", [])
            tags = [ImageTag.objects.get_or_create(**tag_data)[0] for tag_data in tags_data]
            if tags:
                instance.tags.add(*tags)

        # Only update image if it's provided in the request
        if "image" in validated_data and validated_data["image"] is not None:
            instance.image = validated_data["image"]

        instance.save()
        return instance

    class Meta:
        model = Image
        fields = ["uid", "image", "width", "height", "set", "tags", "meta", "created_at", "updated_at"]
