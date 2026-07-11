# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import MagicMock

import factory
from django.test import TestCase

from django_contentdb import models
from django_contentdb.viewsets import PublishedSortMixin


class AttributeSetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AttributeSet


class ContentTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ContentType


class ContentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Content


class DraftFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Draft


class PublishedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Draft


class ContentChannelFactory(factory.django.DjangoModelFactory):
    idx = factory.Sequence(lambda n: f"channel-{n}")
    name = factory.LazyAttribute(lambda o: f"Channel {o.idx}")
    is_default = False

    class Meta:
        model = models.ContentChannel


class ContentDBTestUtils:
    def _create_content(self, x: int, content_type=None):
        result = []
        for _ in range(x):
            record = ContentFactory(content_type=content_type)
            result.append(record)
        return result

    def create_drafts(self, x: int, content_type=None):
        result = []
        content_list = self._create_content(x, content_type)
        for content in content_list:
            record = DraftFactory(content=content)
            result.append(record)
        return result

    def create_published(self, x: int, drafts: list):
        result = []
        for draft in drafts:
            content_type = draft.content.content_type
            content_list = self._create_content(x, content_type)
            for content in content_list:
                record = PublishedFactory(draft=draft, content=content)
                result.append(record)
        return result


class DraftTestCase(TestCase):
    def test_list(self):
        attr_set = AttributeSetFactory()
        content_type = ContentTypeFactory(attribute_set=attr_set)
        drafts = ContentDBTestUtils().create_drafts(10, content_type)
        # TODO


def _make_request(*sort_values: str) -> MagicMock:
    req = MagicMock()
    req.query_params.getlist.return_value = list(sort_values)
    return req


def _make_queryset() -> MagicMock:
    qs = MagicMock()
    qs.order_by.return_value = qs
    qs.distinct.return_value = qs
    return qs


class _SortView(PublishedSortMixin):
    available_sorting_fields = ["created_at", "updated_at"]
    default_sorting_field = "-created_at"
    distinct_fields = ["published__draft"]


class PublishedSortMixinTest(TestCase):
    def test_default_sort_maps_created_at(self):
        view = _SortView()
        qs = _make_queryset()
        view.sort(_make_request(), qs)
        qs.order_by.assert_called_once_with("-published__draft__created_at")

    def test_custom_created_at_remapped(self):
        view = _SortView()
        qs = _make_queryset()
        view.sort(_make_request("created_at"), qs)
        qs.order_by.assert_called_once_with("published__draft__created_at")

    def test_custom_minus_created_at_remapped(self):
        view = _SortView()
        qs = _make_queryset()
        view.sort(_make_request("-created_at"), qs)
        qs.order_by.assert_called_once_with("-published__draft__created_at")

    def test_arbitrary_field_rejected(self):
        view = _SortView()
        qs = _make_queryset()
        view.sort(_make_request("secret_field"), qs)
        qs.order_by.assert_not_called()

    def test_no_available_sorting_fields_returns_queryset_unchanged(self):
        class _NoFields(PublishedSortMixin):
            default_sorting_field = None

        view = _NoFields()
        qs = _make_queryset()
        result = view.sort(_make_request("created_at"), qs)
        qs.order_by.assert_not_called()
        assert result is qs
