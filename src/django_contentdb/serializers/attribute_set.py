# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers

from django_contentdb.models import Attribute, AttributeSet


class AttributeSetSerializer(serializers.ModelSerializer):
    attributes = serializers.SlugRelatedField(slug_field="slug", queryset=Attribute.objects.all(), many=True)

    class Meta:
        model = AttributeSet
        fields = ["slug", "label", "attributes"]
