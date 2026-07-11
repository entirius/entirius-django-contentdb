# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_filters import rest_framework as django_filters
from rest_framework.permissions import AllowAny

from django_contentdb.filters import RouteFilter
from django_contentdb.models import Route
from django_contentdb.serializers import RouteSerializer
from django_contentdb.viewsets import ROContentDBModelViewSet as ReadOnlyModelViewSet


class RORouteViewSet(ReadOnlyModelViewSet):
    queryset = Route.objects.exclude(label="").order_by("url")
    serializer_class = RouteSerializer
    filter_backends = (django_filters.DjangoFilterBackend,)
    filterset_class = RouteFilter
    authentication_classes = []
    permission_classes = [AllowAny]
    lookup_field = "url"
