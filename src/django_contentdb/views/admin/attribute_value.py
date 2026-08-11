# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_contentdb.models import Attribute, AttributeValue
from django_contentdb.permissions import ContentTypePermission
from django_contentdb.serializers import AttributeValueSerializer
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ContentDBModelViewSet as ModelViewSet


class AttributeValueViewSet(ModelViewSet):
    """
    API endpoint that allows documents to be viewed or edited.
    """

    queryset = AttributeValue.objects.all().order_by("-created_at")
    attribute_model = Attribute
    serializer_class = AttributeValueSerializer
    pagination_class = StandardPagination
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated & (IsAdminUser | ContentTypePermission)]
    lookup_field = "pk"

    def get_attribute(self):
        slug = self.kwargs.get("attribute_slug", None)
        try:
            return self.attribute_model.objects.get(slug=slug)
        except ObjectDoesNotExist:
            raise NotFound

    def get_queryset(self):
        attr = self.get_attribute()
        query = super().get_queryset()
        return query.filter(attribute=attr)

    def get_serializer_context(self):
        attr = self.get_attribute()
        context = super().get_serializer_context()
        context.update({"attribute": attr})
        return context
