# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ObjectDoesNotExist
from django_filters import rest_framework as django_filters
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny

from django_contentdb.filters import DraftFilter
from django_contentdb.models import Content, ContentType
from django_contentdb.serializers import DraftContentSerializer
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ROContentDBModelViewSet as ReadOnlyModelViewSet


class RODraftViewSet(ReadOnlyModelViewSet):
    """
    API endpoint that allows documents to be viewed or edited.
    """

    content_type_model = ContentType
    queryset = Content.objects.all()
    serializer_class = DraftContentSerializer
    filter_backends = (django_filters.DjangoFilterBackend,)
    filterset_class = DraftFilter
    pagination_class = StandardPagination
    authentication_classes = []
    permission_classes = [AllowAny]
    lookup_field = "uid"

    def get_content_type(self):
        slug = self.kwargs.get("content_type", None)
        try:
            return self.content_type_model.objects.get(slug=slug, is_layout_extender=False)
        except ObjectDoesNotExist:
            raise NotFound

    def get_queryset(self, *args, **kwargs):
        c_type = self.kwargs.get("content_type", None)
        if not ContentType.objects.filter(slug=c_type).exists():
            raise NotFound
        return self.queryset.filter(
            draft__isnull=False,
            draft__content_type__slug=c_type,
            published__isnull=False,
        ).prefetch_related("draft__channels")

    def get_serializer_context(self):
        c_type_slug = self.kwargs.get("content_type", None)
        try:
            c_type = ContentType.objects.get(slug=c_type_slug)
        except ObjectDoesNotExist:
            raise NotFound
        context = super().get_serializer_context()
        context.update({"_type": c_type})
        return context

    def list(self, request, *args, **kwargs):
        res = super().list(request, *args, **kwargs)
        ct = self.get_content_type()
        res.data = {**res.data, "content_type": ct.slug}
        return res


class ROLayoutViewSet(RODraftViewSet):
    def get_content_type(self):
        slug = self.kwargs.get("content_type", None)
        try:
            return self.content_type_model.objects.get(slug=slug, is_layout_extender=True)
        except ObjectDoesNotExist:
            raise NotFound
