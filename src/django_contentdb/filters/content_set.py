# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_filters import rest_framework as filters

from django_contentdb.models import ContentSet


class ContentSetFilter(filters.FilterSet):
    content_type = filters.ModelChoiceFilter(
        field_name="members__content_type__slug", to_field_name="slug", queryset=ContentSet.objects.all()
    )
