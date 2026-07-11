# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path

from django_contentdb.api.v2.views.author_views import AuthorViewSet
from django_contentdb.api.v2.views.navigation_views import NavigationViewSet

author_list = AuthorViewSet.as_view({"get": "list", "post": "create"})
author_detail = AuthorViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"})
navigation_view = NavigationViewSet.as_view({"get": "retrieve"})

urlpatterns = [
    path("admin/authors/", author_list, name="author-list"),
    path("admin/authors/<uuid:uid>/", author_detail, name="author-detail"),
    path("navigation/<str:content_type_slug>/", navigation_view, name="navigation-published"),
]
