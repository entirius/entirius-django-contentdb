# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers

from django_contentdb.models import Route


class RouteSerializer(serializers.ModelSerializer):
    draft = serializers.StringRelatedField(read_only=True, required=False, default=None, allow_null=True)

    class Meta:
        model = Route
        fields = ["url", "label", "placement", "draft"]
