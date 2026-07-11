# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from django_contentdb.models import Category


class CategoryField(serializers.RelatedField):
    def to_representation(self, value):
        return {
            "uid": value.uid,
            "name": value.name,
            "url_key": value.url_key,
            "language": value.language.iso2 if value.language else None,
        }

    def to_internal_value(self, data):
        try:
            if isinstance(data, dict):
                return Category.objects.get(uid=data.get("uid"))
            else:
                return Category.objects.get(uid=data)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(f"Category with uid {data} does not exist")
