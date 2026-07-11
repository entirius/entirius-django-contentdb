# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework.permissions import IsAdminUser, IsAuthenticated

from django_contentdb.models import ContentType
from django_contentdb.permissions import ContentTypePermission
from django_contentdb.serializers import ContentTypeSerializer
from django_contentdb.utils import DjangoAuth as TokenAuthentication
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ContentDBModelViewSet as ModelViewSet


class ContentTypeViewSet(ModelViewSet):
    """
    API endpoint that allows doc types to be viewed or edited.
    """

    queryset = ContentType.objects.filter(is_layout_extender=False).order_by("-created_at")
    serializer_class = ContentTypeSerializer
    pagination_class = StandardPagination
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated & (IsAdminUser | ContentTypePermission)]
    lookup_field = "slug"


class LayoutTypeViewSet(ContentTypeViewSet):
    queryset = ContentType.objects.filter(is_layout_extender=True).order_by("-created_at")
