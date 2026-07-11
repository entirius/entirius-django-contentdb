# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers

from django_contentdb.models import AttributeValue


class AttributeValueSerializer(serializers.Serializer):
    class Meta:
        model = AttributeValue
        fields = ["id", "value"]
        read_only_fields = ["id"]

    def to_representation(self, instance):
        result = {"id": instance.pk, "value": instance.value}
        return result

    def to_internal_value(self, data):
        attribute = self.context["attribute"]
        input_value_type = attribute.type_as_str
        input_value = attribute.parse_value(data["value"])
        result = {
            "value_bool": None,
            "value_int": None,
            "value_txt": None,
            "value_txt_t9n": None,
            "value_txt_long": None,
            "value_datetime": None,
            f"value_{input_value_type}": input_value,
        }
        return result

    def create(self, validated_data):
        attribute = self.context["attribute"]
        ModelClass = self.Meta.model
        instance, _ = ModelClass.objects.get_or_create(attribute=attribute, **validated_data)
        return instance

    def update(self, instance, validated_data):
        for key in validated_data:
            setattr(instance, key, validated_data[key])
        instance.save()
        return instance
