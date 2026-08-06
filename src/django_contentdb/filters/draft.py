# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db.models import Q
from django_filters import BooleanFilter, CharFilter, ModelMultipleChoiceFilter

from django_contentdb.filters import ContentFilter
from django_contentdb.models import AccessRights, Route


class DraftFilter(ContentFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        access_rights = ModelMultipleChoiceFilter(
            field_name="draft__access_rights__access_level",
            to_field_name="access_level",
            queryset=AccessRights.objects.all(),
        )
        route_filter = ModelMultipleChoiceFilter(
            field_name="draft__routes__url", to_field_name="url", queryset=Route.objects.all()
        )

        language_filter = CharFilter(method=self._filter_by_language)

        channel_filter = CharFilter(method=self.filter_channel)

        self.__dict__["filters"].update(
            {
                "access_rights": access_rights,
                "access_rights[]": access_rights,
                "routes": route_filter,
                "routes[]": route_filter,
                "language": language_filter,
                "channel": channel_filter,
                "exclude_in_content_set": BooleanFilter(method=self.filter_exclude_in_content_set),
                "author": CharFilter(method=self.filter_author),
                "name": CharFilter(method=self.filter_name),
            }
        )

    @staticmethod
    def _filter_by_language(queryset, name, value):
        return queryset.filter(draft__language__iso2__iexact=value)

    def filter_exclude_in_content_set(self, queryset, name, value):
        if value:
            return queryset.filter(draft__drafttocontentset__isnull=True)
        return queryset

    def filter_channel(self, queryset, name, value):
        if value:
            return queryset.filter(Q(draft__channels__idx=value) | Q(draft__channels__isnull=True)).distinct()
        return queryset

    def filter_name(self, queryset, name, value):
        if value:
            return queryset.filter(draft__name__icontains=value)
        return queryset

    def filter_author(self, queryset, name, value):
        if value:
            q = Q(draft__draft_authors__author__slug=value) | Q(draft__draft_co_authors__author__slug=value)
            try:
                from uuid import UUID

                uid = UUID(value)
                q = q | Q(draft__draft_authors__author__uid=uid) | Q(draft__draft_co_authors__author__uid=uid)
            except ValueError:
                pass
            return queryset.filter(q).distinct()
        return queryset
