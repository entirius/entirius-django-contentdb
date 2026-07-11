# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_filters import rest_framework as django_filters
from rest_framework.permissions import AllowAny

from django_contentdb.filters import ImageFilter
from django_contentdb.models import Image
from django_contentdb.serializers import ImageSerializer
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ROContentDBModelViewSet as ReadOnlyModelViewSet


class ROImageViewSet(ReadOnlyModelViewSet):
    """
    API endpoint that allows documents to be viewed or edited.
    """

    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    filter_backends = (django_filters.DjangoFilterBackend,)
    filterset_class = ImageFilter
    pagination_class = StandardPagination
    authentication_classes = []
    permission_classes = [AllowAny]
    lookup_field = "uid"
