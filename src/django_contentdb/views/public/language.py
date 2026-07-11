# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework.permissions import AllowAny

from django_contentdb.models import Language
from django_contentdb.serializers import LanguageSerializer
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ROContentDBModelViewSet as ReadOnlyModelViewSet


class ROLanguageViewSet(ReadOnlyModelViewSet):
    """
    API endpoint that allows documents to be viewed or edited.
    """

    queryset = Language.objects.all().order_by("-iso2")
    serializer_class = LanguageSerializer
    # filter_backends = (django_filters.DjangoFilterBackend,)
    # filterset_class = ...
    pagination_class = StandardPagination
    authentication_classes = []
    permission_classes = [AllowAny]
    lookup_field = "iso2"
