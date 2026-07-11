# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_filters import rest_framework as django_filters
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from django_contentdb.filters import ImageFilter
from django_contentdb.models import Image
from django_contentdb.permissions import ContentTypePermission
from django_contentdb.serializers import ImageSerializer
from django_contentdb.utils import DjangoAuth as TokenAuthentication
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ContentDBModelViewSet as ModelViewSet


class ImageViewSet(ModelViewSet):
    """
    API endpoint that allows images to be viewed or edited.
    """

    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    filter_backends = (django_filters.DjangoFilterBackend,)
    filterset_class = ImageFilter
    pagination_class = StandardPagination
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated & (IsAdminUser | ContentTypePermission)]
    lookup_field = "uid"
