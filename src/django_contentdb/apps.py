# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.apps import AppConfig


class ContentdbConfig(AppConfig):
    name = "django_contentdb"
    verbose_name = "Content Database"
    is_volkanos = True
    # Copied 1:1 from entirius-django-access cf538d2 catalogue defaults;
    # the access defaults stay until this module's release.
    access_areas = [
        {"key": "content.pages", "label": "Pages, layouts, routes and blog"},
        {"key": "content.publish", "label": "Publish and unpublish content", "levels": ("write",)},
        {"key": "content.media", "label": "Images and image tags"},
        {"key": "content.schema", "label": "Content types, sets, attributes and languages"},
    ]
    # DraftViewSet and LayoutViewSet serve their pages and their `…/published` actions: one class, two areas,
    # so their routes keep path rules: the default published rule 1:1, then the default catch-all narrowed to their
    # two router prefixes (no catch-all). Every other admin view carries access_area.
    access_route_rules = [
        {
            "pattern": r"api-admin/contentdb/[^/]+/(?:content|layout-extender)/.*/published(?=/|\\)",
            "area": "content.publish",
        },
        {"pattern": r"api-admin/contentdb/[^/]+/(?:content|layout-extender)/", "area": "content.pages"},
    ]

    def ready(self):
        # Implicitly connect all signal handlers decorated with @receiver.
        pass
