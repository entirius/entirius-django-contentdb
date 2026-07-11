# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ObjectDoesNotExist
from django_utils.api.v2_errors import raise_pydantic_as_drf
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from pydantic import ValidationError as PydanticValidationError
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_contentdb.api.v2.pagination import AdminPageNumberPagination
from django_contentdb.schemas.requests.author import CreateAuthorRequest, DeleteAuthorRequest, UpdateAuthorRequest
from django_contentdb.schemas.responses.author import AuthorListResponse, AuthorResponse
from django_contentdb.services import author_service


@extend_schema_view(
    list=extend_schema(tags=["Authors"]),
    create=extend_schema(tags=["Authors"]),
    retrieve=extend_schema(tags=["Authors"]),
    partial_update=extend_schema(tags=["Authors"]),
    destroy=extend_schema(tags=["Authors"]),
)
class AuthorViewSet(viewsets.ViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    pagination_class = AdminPageNumberPagination

    @extend_schema(
        summary="List authors",
        description="Returns paginated list of authors with published post counts.",
        parameters=[
            OpenApiParameter(name="search", description="Search by name or slug"),
            OpenApiParameter(name="is_active", description="Filter by active status", type=bool),
            OpenApiParameter(name="channel", description="Channel idx for post count scoping"),
            OpenApiParameter(name="page", description="Page number", type=int),
            OpenApiParameter(name="page_size", description="Items per page (max 100)", type=int),
        ],
        responses={200: AuthorListResponse},
    )
    def list(self, request):
        search = request.query_params.get("search")
        is_active_param = request.query_params.get("is_active")
        channel = request.query_params.get("channel")

        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1")

        queryset = author_service.list_authors(search=search, is_active=is_active, channel_idx=channel)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            data = [author_service.serialize_author(a, request=request) for a in page]
            return paginator.get_paginated_response(data)

        data = [author_service.serialize_author(a, request=request) for a in queryset]
        return Response(data)

    @extend_schema(
        summary="Create author",
        description="Create a new author profile. Slug auto-generated from name if not provided.",
        request=CreateAuthorRequest,
        responses={201: AuthorResponse},
    )
    def create(self, request):
        try:
            schema = CreateAuthorRequest(**request.data)
        except PydanticValidationError as exc:
            raise_pydantic_as_drf(exc)
        author = author_service.create_author(schema.model_dump())
        author = author_service.get_author_detail(author.uid)
        return Response(author_service.serialize_author(author, request=request), status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Retrieve author by UID",
        description="Returns a single author with published post count.",
        parameters=[OpenApiParameter(name="uid", location="path", description="Author UUID")],
        responses={200: AuthorResponse},
    )
    def retrieve(self, request, uid=None):
        try:
            author = author_service.get_author_detail(uid)
        except ObjectDoesNotExist:
            raise NotFound
        return Response(author_service.serialize_author(author, request=request))

    @extend_schema(
        summary="Update author",
        description="Partial update of an author profile.",
        parameters=[OpenApiParameter(name="uid", location="path", description="Author UUID")],
        request=UpdateAuthorRequest,
        responses={200: AuthorResponse},
    )
    def partial_update(self, request, uid=None):
        try:
            schema = UpdateAuthorRequest(**request.data)
        except PydanticValidationError as exc:
            raise_pydantic_as_drf(exc)
        try:
            author_service.update_author(uid, schema.model_dump(exclude_unset=True))
            author = author_service.get_author_detail(uid)
        except ObjectDoesNotExist:
            raise NotFound
        return Response(author_service.serialize_author(author, request=request))

    @extend_schema(
        summary="Delete author",
        description="Delete an author. Optionally reassign their posts to another author.",
        parameters=[OpenApiParameter(name="uid", location="path", description="Author UUID")],
        request=DeleteAuthorRequest,
        responses={204: None},
    )
    def destroy(self, request, uid=None):
        try:
            schema = DeleteAuthorRequest(**request.data) if request.data else DeleteAuthorRequest()
        except PydanticValidationError as exc:
            raise_pydantic_as_drf(exc)
        try:
            author_service.delete_author(uid, reassign_to=schema.reassign_to)
        except ObjectDoesNotExist:
            raise NotFound
        return Response(status=status.HTTP_204_NO_CONTENT)
