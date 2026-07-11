# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db.models import Exists, OuterRef
from rest_framework.permissions import AllowAny

from django_contentdb.models import Category, Content
from django_contentdb.serializers import CategorySerializer
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ROContentDBModelViewSet as ReadOnlyModelViewSet


class ROCategoryViewSet(ReadOnlyModelViewSet):
    """
    API endpoint that allows categories to be viewed.

    Query params:
    - language: Filter by language ISO2 code (e.g., ?language=pl). If not provided, returns all categories.
    - access_rights: Filter by access rights levels (e.g., ?access_rights=1,2)
    """

    queryset = Category.objects.all().order_by("-created_at")
    serializer_class = CategorySerializer
    pagination_class = StandardPagination
    authentication_classes = []
    permission_classes = [AllowAny]
    lookup_field = "uid"

    def get_queryset(self):
        queryset = super().get_queryset()
        access_rights = self.request.query_params.get("access_rights", None)
        language_iso2 = self.request.query_params.get("language", None)

        # Filter by language
        if language_iso2:
            queryset = queryset.filter(language__iso2=language_iso2)

        # Filter by published content
        published_content = Content.objects.filter(category=OuterRef("pk"), published__isnull=False)

        if access_rights:
            access_levels = [int(level) for level in access_rights.split(",")]
            published_content = published_content.filter(
                published__draft__access_rights__access_level__in=access_levels
            )
        return queryset.filter(Exists(published_content))

    def list(self, request, *args, **kwargs):
        res = super().list(request, *args, **kwargs)
        filtered_data = [item for item in res.data["data"] if item["published_posts_count"] > 0]
        res.data["data"] = filtered_data
        res.data["pagination"]["records"] = len(filtered_data)
        return res
