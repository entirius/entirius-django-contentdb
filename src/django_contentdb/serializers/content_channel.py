# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers
from rest_framework.relations import SlugRelatedField

from django_contentdb.models import ContentChannel, Language


class ContentChannelSerializer(serializers.ModelSerializer):
    default_language = SlugRelatedField(
        slug_field="iso2", queryset=Language.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = ContentChannel
        fields = ["idx", "name", "default_language", "is_default"]
