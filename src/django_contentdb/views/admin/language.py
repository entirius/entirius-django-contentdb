# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_contentdb.models import Language
from django_contentdb.permissions import ContentTypePermission
from django_contentdb.serializers import LanguageSerializer
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ROContentDBModelViewSet as ReadOnlyModelViewSet


class LanguageViewSet(ReadOnlyModelViewSet):
    """
    API endpoint that allows languages to be viewed or edited.
    """

    queryset = Language.objects.all().order_by("-iso2")
    serializer_class = LanguageSerializer
    # filter_backends = (django_filters.DjangoFilterBackend,)
    # filterset_class = ...
    pagination_class = StandardPagination
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (IsAdminUser | ContentTypePermission)]
    lookup_field = "iso2"
