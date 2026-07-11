# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from itertools import groupby

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from django_contentdb.models import Attribute, AttributeValue, Category, Content
from django_contentdb.serializers.fields import CategoryField


class ContentSerializer(serializers.ModelSerializer):
    class AttributesField(serializers.JSONField):
        def to_representation(self, instances) -> dict:
            result = {}
            key = lambda elem: elem.attribute.slug
            groups = groupby(sorted(instances.all(), key=key), key=key)
            for group_key, group in groups:
                vals = [elem.value for elem in group]
                result[group_key] = vals
            return result

        def to_internal_value(self, data) -> list[AttributeValue]:
            def get_attribute(slug) -> Attribute:
                try:
                    instance = Attribute.objects.get(slug=slug)
                except ObjectDoesNotExist:
                    raise ValidationError(f"Unsupported attribute {slug}")
                return instance

            def get_attribute_value(instance: Attribute, value) -> AttributeValue:
                try:
                    parsed_value = instance.parse_value(value)
                    kwargs = {f"value_{instance.type_as_str}": parsed_value}
                except NotImplementedError:
                    raise ValidationError("Unsupported attribute type")
                except ValueError:
                    raise ValidationError(
                        f"Given value does not match attribute {instance.slug} type: should be {instance.type_as_str}"
                    )
                except Exception as e:
                    raise ValidationError(f"Error during attribute serialization: {e}")

                if instance.allow_new_values:
                    value_instance, _ = AttributeValue.objects.get_or_create(attribute=instance, **kwargs)
                else:
                    try:
                        value_instance = AttributeValue.objects.get(attribute=instance, **kwargs)
                    except ObjectDoesNotExist:
                        raise ValidationError(
                            f"Value {next(iter(kwargs.values()))} is not allowed for attribute {instance}"
                        )
                return value_instance

            parsed = super().to_internal_value(data)
            if not parsed:
                result = []
            else:
                result = []
                for key in parsed:
                    attr = get_attribute(key)
                    if isinstance(parsed[key], list):
                        if attr.allow_many_values:
                            for elem in parsed[key]:
                                result.append(get_attribute_value(attr, elem))
                        else:
                            raise ValidationError(f"Multiple values are not allowed for {attr}")
                    else:
                        result.append(get_attribute_value(attr, parsed[key]))
            return result

    class HasExtensionField(serializers.Field):
        def to_representation(self, value: dict):
            return value is not None and len(value) > 0

    def validate_attributes(self, value):
        _type = self.context.get("_type")
        attribute_set = _type.attribute_set
        for elem in value:
            attribute = elem.attribute
            is_valid = attribute.attribute_sets.filter(pk=attribute_set.pk).exists()
            if not is_valid:
                raise ValidationError(f"Attribute '{attribute}' does not belong to Content Type '{_type}'")
        return value

    uid = serializers.UUIDField(read_only=True)
    attributes = AttributesField()
    has_extension = HasExtensionField(read_only=True, source="extension")
    extension = serializers.JSONField(required=False, default=None, allow_null=True)
    category = CategoryField(queryset=Category.objects.all(), required=False, default=None, allow_null=True)

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

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
        ]
