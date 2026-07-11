# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers

from django_contentdb.models import AttributeSet, ContentType


class ContentTypeSerializer(serializers.ModelSerializer):
    class AttributesInTypeField(serializers.Field):
        def to_representation(self, value) -> list:
            result = [
                {
                    "slug": attr.slug,
                    "lable": attr.label,
                    "type": attr.type_as_str,
                    "is_filterable": attr.is_filterable,
                    "is_searchable": attr.is_searchable,
                    "is_comparable": attr.is_comparable,
                    "allow_new_values": attr.allow_new_values,
                    "allow_many_values": attr.allow_many_values,
                }
                for attr in value.attributes.all()
            ]
            return result

    attribute_set = serializers.SlugRelatedField(slug_field="slug", queryset=AttributeSet.objects.all())
    attributes = AttributesInTypeField(read_only=True, source="attribute_set")

    class Meta:
        model = ContentType
        fields = ["slug", "label", "attribute_set", "attributes", "is_layout_extender", "supports_authors"]
