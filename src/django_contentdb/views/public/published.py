# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Prefetch
from django_filters import rest_framework as django_filters
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django_contentdb.filters import PublishedFilter
from django_contentdb.models import Content, ContentType, DraftAuthor, DraftCoAuthor
from django_contentdb.serializers import PublishedContentSerializer
from django_contentdb.services import navigation_service
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import PublishedSortMixin, ROContentDBModelViewSet


class ROPublishedViewSet(PublishedSortMixin, ROContentDBModelViewSet):
    content_type_model = ContentType
    queryset = Content.objects.all()
    serializer_class = PublishedContentSerializer
    filter_backends = (django_filters.DjangoFilterBackend,)
    filterset_class = PublishedFilter
    pagination_class = StandardPagination
    authentication_classes = []
    permission_classes = [AllowAny]
    lookup_field = "uid"
    distinct_fields = ["published__draft_id"]
    available_sorting_fields = ["created_at", "updated_at"]
    default_sorting_field = "-created_at"

    def get_content_type(self):
        slug = self.kwargs.get("content_type", None)
        try:
            return self.content_type_model.objects.get(slug=slug)
        except ObjectDoesNotExist:
            raise NotFound

    def get_queryset(self):
        queryset = super().get_queryset()
        content_type = self.get_content_type()

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

        # Storefront fetches single articles via `?routes=<slug>` on this list endpoint
        # (it does not call retrieve by uid). When the filter resolves to a single item,
        # populate prev/next so SEO `<link rel="prev/next">` works without an extra
        # round-trip. Tile lists (no routes filter) stay null per the API contract —
        # neighbours don't make sense per-tile.
        items = res.data.get("data") if isinstance(res.data, dict) else None
        if request.query_params.get("routes") and isinstance(items, list) and len(items) == 1:
            siblings = navigation_service.get_published_siblings(
                content_uid=items[0]["uid"],
                content_type_slug=ct.slug,
                channel_idx=request.query_params.get("channel"),
                language_iso2=request.query_params.get("language"),
            )
            items[0]["prev"] = siblings["prev"]
            items[0]["next"] = siblings["next"]
        return res

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single Published — adds prev/next siblings to the response.

        Computes siblings once and injects them into ``serializer.context["siblings"]``
        so the serializer's ``prev``/``next`` fields are populated without doing any
        extra ORM work themselves. List response keeps ``prev``/``next`` as ``null``
        unless filtered to a single item via ``?routes=`` (see :meth:`list`).
        """
        instance = self.get_object()
        ct = self.get_content_type()
        siblings = navigation_service.get_published_siblings(
            content_uid=str(instance.uid),
            content_type_slug=ct.slug,
            channel_idx=request.query_params.get("channel"),
            language_iso2=request.query_params.get("language"),
        )
        serializer = self.get_serializer(instance)
        serializer.context["siblings"] = siblings
        return Response({"meta": {"status": "OK", "message": ""}, "data": serializer.data})


class ROLayoutPublishedViewSet(ROPublishedViewSet):
    queryset = Content.objects.all()
    filterset_class = PublishedFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        content_type = self.get_content_type()
        result = queryset.filter(
            published__draft__content_type=content_type,
            published__draft__content_type__is_layout_extender=True,
            published__isnull=False,
        )
        return result
