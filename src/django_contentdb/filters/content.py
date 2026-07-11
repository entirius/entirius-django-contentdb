# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from functools import reduce
from operator import or_

from django.db.models import Exists, OuterRef, Q, QuerySet, Subquery
from django_filters import CharFilter, UUIDFilter
from django_filters import rest_framework as filters

from django_contentdb.models import Attribute, AttributeValue, Content


def filters_from_attributes(queryset: QuerySet, _type="content") -> dict[str, filters.CharFilter]:
    """generates dictionary of filter functions
    based on provided attributes"""

    type_query = {f"{_type}_set__pk": OuterRef("pk")}

    def filter_from_attribute(obj: Attribute) -> tuple[str, filters.CharFilter]:
        def filter_by_value(queryset, name, value):
            try:
                parsed_value = obj.parse_value(value)
            except ValueError:
                return queryset
            value_query = {f"value_{obj.type_as_str}": parsed_value}
            attr = AttributeValue.objects.filter(attribute__slug=name, **value_query, **type_query)
            return queryset.filter(Exists(attr))

        return obj.slug, filters.CharFilter(field_name=obj.slug, method=filter_by_value)

    filterable = (obj for obj in queryset if obj.is_filterable)
    pairs = (filter_from_attribute(obj) for obj in filterable)
    result = {name: filter_obj for name, filter_obj in pairs}
    return result


def order_by_from_attributes(attributes, _type="content") -> dict[str, filters.CharFilter]:
    """generates dictionary containing order_by filter function
    based on provided attributes"""

    type_query = {f"{_type}_set__pk": OuterRef("pk")}

    def order_by_attribute(queryset, name, value):
        slug = str(value).strip("-")
        ascending = False if str(value)[0] == "-" else True
        attribute = next((obj for obj in attributes if obj.slug == slug and obj.is_comparable), None)
        if attribute is not None:
            value_type = f"value_{attribute.type_as_str}"
            subquery = Subquery(AttributeValue.objects.filter(attribute=attribute, **type_query).values(value_type)[:1])
            if ascending:
                return queryset.order_by(subquery.asc())
            else:
                return queryset.order_by(subquery.desc())
        else:
            return queryset

    filter_obj = filters.CharFilter(field_name="order-by", method=order_by_attribute)

    return {"order-by": filter_obj}


def search_from_attributes(attributes, _type="content") -> dict[str, filters.CharFilter]:
    """generates dictionary containing search filter function
    based on provided attributes"""

    type_query = {f"{_type}_set__pk": OuterRef("pk")}

    def generate_q_object(attributes, value):
        searchable = (obj for obj in attributes if obj.is_searchable)
        valid = (obj for obj in searchable if obj.is_txt or obj.is_txt_long)
        queries = ({f"value_{obj.type_as_str}__icontains": value} for obj in valid)
        q_objects = (Q(**query) for query in queries)
        result = reduce(or_, q_objects, Q(pk__isnull=True))
        return result

    def search(queryset, name, value):
        q_object = generate_q_object(attributes, value)
        subquery = AttributeValue.objects.filter(q_object, **type_query)
        return queryset.filter(Exists(subquery))

    filter_obj = filters.CharFilter(field_name="search", method=search)

    return {"search": filter_obj}


class ContentFilter(filters.FilterSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = kwargs.get("queryset")
        elem = qs.first()
        _type = (
            elem.draft.content_type
            if elem is not None and hasattr(elem, "draft")
            else elem.published.draft.content_type
            if elem is not None and hasattr(elem, "published")
            else None
        )
        if _type is not None:
            attributes = [obj for obj in _type.attribute_set.attributes.all()]
            # generate filter functions based on attribute set
            filters_to_add = {
                **filters_from_attributes(attributes),
                **order_by_from_attributes(attributes),
                **search_from_attributes(attributes),
            }
            # assign filter functions to FilterSet
            self.__dict__["filters"].update(filters_to_add)
        category_filter = UUIDFilter(field_name="category__uid")
        self.__dict__["filters"].update({"category": category_filter})

        category_url_key_filter = CharFilter(field_name="category__url_key")
        self.__dict__["filters"].update({"category_url_key": category_url_key_filter})

    class Meta:
        model = Content
        fields = {"created_at": ["exact", "gt", "lt"], "updated_at": ["exact", "gt", "lt"]}
