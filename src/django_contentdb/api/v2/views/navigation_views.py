# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django_contentdb.schemas.responses.navigation import NavigationPublishedResponse
from django_contentdb.services import navigation_service


@extend_schema_view(
    retrieve=extend_schema(tags=["Navigation"]),
)
class NavigationViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get published navigation",
        description="Returns published navigation content for the given layout extender type. "
        "Redis-cached for performance. Used by storefronts on every page load.",
        parameters=[
            OpenApiParameter(
                name="content_type_slug", location="path", description="Layout extender content type slug (e.g. header)"
            ),
            OpenApiParameter(name="language", description="ISO2 language code", required=False),
            OpenApiParameter(name="channel", description="Channel idx", required=False),
        ],
        responses={200: NavigationPublishedResponse, 404: None},
    )
    def retrieve(self, request, content_type_slug=None):
        language = request.query_params.get("language")
        channel = request.query_params.get("channel")
        result = navigation_service.get_published_navigation(content_type_slug, language, channel)
        if not result:
            raise NotFound
        return Response(result)
