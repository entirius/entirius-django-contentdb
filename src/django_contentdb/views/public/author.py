# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django_contentdb.serializers.author import PublicAuthorSerializer
from django_contentdb.services import author_service
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ROContentDBModelViewSet as ReadOnlyModelViewSet


class ROAuthorViewSet(ReadOnlyModelViewSet):
    """Public read-only author listing and detail by slug.

    Returns only active authors with at least one published blog post.
    Accepts optional ?channel= query param to scope post count to a specific channel.
    """

    serializer_class = PublicAuthorSerializer
    pagination_class = StandardPagination
    authentication_classes = []
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        channel = self.request.query_params.get("channel")
        return author_service.list_public_authors(channel_idx=channel)

    def retrieve(self, request, *args, **kwargs):
        slug = kwargs.get("slug", "")
        channel = request.query_params.get("channel")
        try:
            author = author_service.get_author_by_slug(slug, channel_idx=channel)
        except ObjectDoesNotExist:
            raise NotFound from None
        serializer = self.get_serializer(author)
        return Response({"meta": {"status": "OK", "message": ""}, "data": serializer.data})
