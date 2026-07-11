# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_filters import ModelMultipleChoiceFilter
from django_filters import rest_framework as filters

from django_contentdb.models import Image, ImageTag


class ImageFilter(filters.FilterSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tag_filter = ModelMultipleChoiceFilter(
            field_name="tags__slug", to_field_name="slug", queryset=ImageTag.objects.all()
        )
        self.__dict__["filters"].update({"tags": tag_filter, "tags[]": tag_filter})

    class Meta:
        model = Image
        fields = {"created_at": ["exact", "gt", "lt"], "updated_at": ["exact", "gt", "lt"]}
