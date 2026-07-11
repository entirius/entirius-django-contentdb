# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import include, path
from rest_framework import routers

from django_contentdb import settings
from django_contentdb.views import admin, public

public_router = routers.DefaultRouter()
public_router.register(r"attributes", public.ROAttributeViewSet, "public_attributes")
public_router.register(
    r"attributes/(?P<attribute_slug>[^/.]+)/values", public.ROAttributeValueViewSet, "public_attribute_values"
)
public_router.register(r"routes", public.RORouteViewSet, "public_routes")
public_router.register(r"attribute-sets", public.ROAttributeSetViewSet, "public_attribute_sets")
public_router.register(r"content-types", public.ROContentTypeViewSet, "public_content_types")
public_router.register(r"content-sets", public.ROContentSetViewSet, "public_content_sets")
public_router.register(r"content/(?P<content_type>[^/.]+)", public.RODraftViewSet, "public_content")
public_router.register(r"published/(?P<content_type>[^/.]+)", public.ROPublishedViewSet, "public_published")
public_router.register(r"layout-extender-types", public.ROLayoutTypeViewSet, "public_layout_types")
public_router.register(r"layout-extender-sets", public.ROLayoutSetViewSet, "public_layout_sets")
public_router.register(r"layout-extender/(?P<content_type>[^/.]+)", public.ROLayoutViewSet, "public_layout")
public_router.register(
    r"layout-extender-published/(?P<content_type>[^/.]+)", public.ROLayoutPublishedViewSet, "public_layout_published"
)
public_router.register(r"image-tags", public.ROImageTagViewSet, "public_image_tags")
public_router.register(r"images", public.ROImageViewSet, "public_image")
public_router.register(r"languages", public.ROLanguageViewSet, "public_language")
public_router.register(r"channels", public.ROContentChannelViewSet, "public_channels")
public_router.register(r"category", public.ROCategoryViewSet, "public_category")
public_router.register(r"authors", public.ROAuthorViewSet, "public_authors")

admin_router = routers.DefaultRouter()
admin_router.register(r"attributes", admin.AttributeViewSet, "admin_attributes")
admin_router.register(
    r"attributes/(?P<attribute_slug>[^/.]+)/values", admin.AttributeValueViewSet, "admin_attribute_values"
)
admin_router.register(r"routes", admin.RouteViewSet, "admin_routes")
admin_router.register(r"attribute-sets", admin.AttributeSetViewSet, "admin_attribute_sets")
admin_router.register(r"content-types", admin.ContentTypeViewSet, "admin_content_types")
admin_router.register(r"content-sets", admin.ContentSetViewSet, "admin_content_setss")
admin_router.register(r"content/(?P<content_type>[^/.]+)", admin.DraftViewSet, "admin_content")
admin_router.register(r"published/(?P<content_type>[^/.]+)", admin.PublishedViewSet, "admin_published")
admin_router.register(r"layout-extender-types", admin.LayoutTypeViewSet, "admin_layout_types")
admin_router.register(r"layout-extender-sets", admin.LayoutSetViewSet, "admin_layout_sets")
admin_router.register(r"layout-extender/(?P<content_type>[^/.]+)", admin.LayoutViewSet, "admin_layout")
admin_router.register(
    r"layout-extender-published/(?P<content_type>[^/.]+)", admin.LayoutPublishedViewSet, "admin_layout_published"
)
admin_router.register(r"image-tags", admin.ImageTagViewSet, "admin_image_tags")
admin_router.register(r"images", admin.ImageViewSet, "admin_images")
admin_router.register(r"languages", admin.LanguageViewSet, "admin_image_languages")
admin_router.register(r"channels", admin.ContentChannelViewSet, "admin_channels")
admin_router.register(r"category", admin.CategoryViewSet, "admin_category")

func_views = [
    path("content-permissions/", admin.view_content_permissions, name="admin_content_permissions"),
    path("layout-extender-permissions/", admin.view_layout_permissions, name="admin_layout_permissions"),
]


urlpatterns = [
    path(f"{settings.ADMIN_BASE_URL}/contentdb/<str:version>/", include([*admin_router.urls, *func_views])),
    path(f"{settings.PUBLIC_BASE_URL}/contentdb/<str:version>/", include(public_router.urls)),
    path("api/contentdb/v2/", include("django_contentdb.api.v2.urls")),
]
