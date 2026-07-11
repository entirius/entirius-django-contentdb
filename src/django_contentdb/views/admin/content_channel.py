# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework.permissions import IsAdminUser, IsAuthenticated

from django_contentdb.models import ContentChannel
from django_contentdb.permissions import ContentTypePermission
from django_contentdb.serializers import ContentChannelSerializer
from django_contentdb.utils import DjangoAuth as TokenAuthentication
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ROContentDBModelViewSet as ReadOnlyModelViewSet


class ContentChannelViewSet(ReadOnlyModelViewSet):
    queryset = ContentChannel.objects.all().order_by("idx")
    serializer_class = ContentChannelSerializer
    pagination_class = StandardPagination
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated & (IsAdminUser | ContentTypePermission)]
    lookup_field = "idx"
