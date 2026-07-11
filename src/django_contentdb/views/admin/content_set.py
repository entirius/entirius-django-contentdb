# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_filters import rest_framework as django_filters
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from django_contentdb.filters import ContentSetFilter
from django_contentdb.models import ContentSet
from django_contentdb.permissions import ContentTypePermission
from django_contentdb.serializers import ContentSetSerializer
from django_contentdb.utils import DjangoAuth as TokenAuthentication
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ContentDBModelViewSet as ModelViewSet


class ContentSetViewSet(ModelViewSet):
    """
    API endpoint that allows document sets to be viewed or edited.
    """

    queryset = (
        ContentSet.objects.filter(members__content_type__is_layout_extender=False).order_by("-created_at").distinct()
    )
    serializer_class = ContentSetSerializer
    filter_backends = (django_filters.DjangoFilterBackend,)
    filterset_class = ContentSetFilter
    pagination_class = StandardPagination
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated & (IsAdminUser | ContentTypePermission)]
    lookup_field = "uid"


class LayoutSetViewSet(ContentSetViewSet):
    queryset = ContentSet.objects.filter(members__content_type__is_layout_extender=True).order_by("-created_at")
