# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_filters import ModelMultipleChoiceFilter
from django_filters import rest_framework as filters

from django_contentdb.models import AttributeSet


class AttributeFilter(filters.FilterSet):
    attribute_set = ModelMultipleChoiceFilter(
        field_name="attribute_set__slug", to_field_name="slug", queryset=AttributeSet.objects.all()
    )
