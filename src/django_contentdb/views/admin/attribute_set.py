# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_contentdb.models import AttributeSet
from django_contentdb.permissions import ContentTypePermission
from django_contentdb.serializers import AttributeSetSerializer
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ContentDBModelViewSet as ModelViewSet


class AttributeSetViewSet(ModelViewSet):
    """
    API endpoint that allows doc type specific tags to be viewed or edited.
    """

    queryset = AttributeSet.objects.all().order_by("-created_at")
    serializer_class = AttributeSetSerializer
    pagination_class = StandardPagination
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (IsAdminUser | ContentTypePermission)]
    lookup_field = "slug"
