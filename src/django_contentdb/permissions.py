# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db.models import Q
from rest_framework.permissions import BasePermission

from django_contentdb.enums import Action
from django_contentdb.models import ContentTypePermission as ContentTypePermissionModel

get_content_action = {
    "create": Action.CREATE,
    "update": Action.UPDATE,
    "destroy": Action.DELETE,
    "published": Action.PUBLISH,
    "list": Action.VIEW,
    "retrieve": Action.VIEW,
    "published_create": Action.PUBLISH,
    "published_delete": Action.DELETE,
}


class ContentTypePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if user.is_superuser:
            return True
        else:
            if view.action not in get_content_action:
                raise Exception(f"Action {view.action} not found in possible get_content_actions.")
            action = get_content_action[view.action]
            content_type_slug = view.kwargs.get("content_type", None)
            permission_exists = ContentTypePermissionModel.objects.filter(
                (Q(user=user) | Q(group__user=user)), content_type__slug=content_type_slug, action=action
            ).exists()
            if permission_exists:
                return True
            else:
                return False
