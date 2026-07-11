# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_filters import rest_framework as django_filters
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from django_contentdb.filters import RouteFilter
from django_contentdb.models import Route
from django_contentdb.permissions import ContentTypePermission
from django_contentdb.serializers import RouteSerializer
from django_contentdb.utils import DjangoAuth as TokenAuthentication
from django_contentdb.viewsets import ContentDBModelViewSet as ModelViewSet


class RouteViewSet(ModelViewSet):
    queryset = Route.objects.exclude(label="").order_by("url")
    serializer_class = RouteSerializer
    filter_backends = (django_filters.DjangoFilterBackend,)
    filterset_class = RouteFilter
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated & (IsAdminUser | ContentTypePermission)]
    lookup_field = "url"
