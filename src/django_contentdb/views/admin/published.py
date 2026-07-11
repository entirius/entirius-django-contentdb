# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Prefetch
from django_filters import rest_framework as django_filters
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from django_contentdb.filters import PublishedFilter
from django_contentdb.models import Content, ContentType, DraftAuthor, DraftCoAuthor
from django_contentdb.permissions import ContentTypePermission
from django_contentdb.serializers import PublishedContentSerializer
from django_contentdb.utils import DjangoAuth as TokenAuthentication
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import PublishedSortMixin, ROContentDBModelViewSet


class PublishedViewSet(PublishedSortMixin, ROContentDBModelViewSet):
    content_type_model = ContentType
    queryset = Content.objects.all()
    serializer_class = PublishedContentSerializer
    filter_backends = (django_filters.DjangoFilterBackend,)
    filterset_class = PublishedFilter
    pagination_class = StandardPagination
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated & (IsAdminUser | ContentTypePermission)]
    lookup_field = "uid"
    distinct_fields = ["published__draft_id"]
    available_sorting_fields = ["published__draft__created_at", "updated_at"]
    default_sorting_field = "-published__draft__created_at"

    def get_content_type(self):
        slug = self.kwargs.get("content_type", None)
        try:
            return self.content_type_model.objects.get(slug=slug)
        except ObjectDoesNotExist:
            raise NotFound

    def get_queryset(self):
        queryset = super().get_queryset()
        content_type = self.get_content_type()
        result = queryset.filter(published__isnull=False, published__draft__content_type=content_type)
        # return newest published content for each content
        latest_contents = (
            queryset.filter(published__draft__content_type=content_type, published__isnull=False)
            .values("published__draft")
            .annotate(latest_id=models.Max("id"), latest_created=models.Max("published__created_at"))
            .values_list("latest_id", flat=True)
        )
        result = queryset.filter(id__in=latest_contents)
        return result.prefetch_related(
            "published__draft__channels",
            Prefetch(
                "published__draft__draft_authors",
                queryset=DraftAuthor.objects.select_related("author__photo").order_by("position"),
            ),
            Prefetch(
                "published__draft__draft_co_authors",
                queryset=DraftCoAuthor.objects.select_related("author__photo").order_by("position"),
            ),
        )

    def list(self, request, *args, **kwargs):
        res = super().list(request, *args, **kwargs)
        ct = self.get_content_type()
        res.data = {**res.data, "content_type": ct.slug}
        return res

    @action(detail=True, name="draft-content")
    def draft(self, request, uid=None, *args, **kwargs):
        draft_content = Content.objects.filter(draft__published__content__uid=uid).first()

        serializer = self.get_serializer(draft_content, many=False)
        response = {"meta": {"status": "OK", "message": ""}, "data": serializer.data}
        return Response(response)


class LayoutPublishedViewSet(PublishedViewSet):
    queryset = Content.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        content_type = self.get_content_type()
        result = queryset.filter(
            published__draft__content_type=content_type,
            published__draft__content_type__is_layout_extender=True,
            published__isnull=False,
        )
        return result
