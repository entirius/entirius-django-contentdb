# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_filters import rest_framework as filters

from django_contentdb.models import Route


class RouteFilter(filters.FilterSet):
    class Meta:
        model = Route
        fields = ["placement"]
