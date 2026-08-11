# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_contentdb.models import Category
from django_contentdb.permissions import ContentTypePermission
from django_contentdb.serializers import CategorySerializer
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ContentDBModelViewSet as ModelViewSet


class CategoryViewSet(ModelViewSet):
    """
    API endpoint that allows categories to be viewed or edited.

    Query params:
    - language: Filter by language ISO2 code (e.g., ?language=pl). If not provided, returns all categories.
    """

    queryset = Category.objects.all().order_by("-created_at")
    serializer_class = CategorySerializer
    pagination_class = StandardPagination
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (IsAdminUser | ContentTypePermission)]
    lookup_field = "uid"

    def get_queryset(self):
        queryset = super().get_queryset()
        language_iso2 = self.request.query_params.get("language", None)

        if language_iso2:
            queryset = queryset.filter(language__iso2=language_iso2)

        return queryset
