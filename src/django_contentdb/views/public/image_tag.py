# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework.permissions import AllowAny

from django_contentdb.models import ImageTag
from django_contentdb.serializers import ImageTagSerializer
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ROContentDBModelViewSet as ReadOnlyModelViewSet


class ROImageTagViewSet(ReadOnlyModelViewSet):
    queryset = ImageTag.objects.all().order_by("slug")
    serializer_class = ImageTagSerializer
    pagination_class = StandardPagination
    authentication_classes = []
    permission_classes = [AllowAny]
    lookup_field = "slug"
