# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from itertools import groupby

from django.db.models import Q
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_contentdb.enums import Action
from django_contentdb.models import ContentType, ContentTypePermission


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def view_content_permissions(request, *args, **kwargs):
    user = request.user
    if user.is_superuser:
        values = [
            {"slug": c_type.slug, "label": c_type.label, "actions": Action.values}
            for c_type in ContentType.objects.all()
        ]
    else:
        query = Q(user=user) | Q(group__in=user.groups.all())
        queryset = (
            ContentTypePermission.objects.filter(query)
            .distinct()
            .values("content_type__slug", "content_type__label", "action")
        )
        key_fun = lambda x: (x["content_type__slug"], x["content_type__label"])
        grouped = groupby(sorted(queryset, key=key_fun), key=key_fun)
        values = [
            {"slug": key[0], "label": key[1], "actions": [elem["action"] for elem in group]} for key, group in grouped
        ]

    res_body = {"meta": {"status": "OK", "message": ""}, "data": values}
    return Response(res_body)
