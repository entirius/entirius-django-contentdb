# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers

from django_contentdb.models import Attribute


class AttributeSerializer(serializers.ModelSerializer):
    class ValuesField(serializers.Field):
        def to_representation(self, value_set):
            result = [
                elem.value
                for elem in value_set.all()
                if not (elem.attribute.is_txt_t9n or elem.attribute.is_txt_long) and elem.attribute.is_filterable
            ]
            return result

    attribute_set = serializers.SlugRelatedField("slug", read_only=True)
    filter_values = ValuesField(source="values", read_only=True)
    type = serializers.ReadOnlyField(source="type_as_str")

    class Meta:
        model = Attribute
        fields = [
            "slug",
            "label",
            "attribute_set",
            "filter_values",
            "is_filterable",
            "is_searchable",
            "is_comparable",
            "allow_new_values",
            "allow_many_values",
            "is_bool",
            "is_int",
            "is_txt",
            "is_txt_long",
            "is_datetime",
            "type",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["filter_values"]
