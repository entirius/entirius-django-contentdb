# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.test import TestCase

from django_contentdb.models import AttributeSet, Content, ContentChannel, ContentType, Draft, Language


class DraftChannelsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lang = Language.objects.create(iso2="EN", iso3="ENG")
        cls.attr_set = AttributeSet.objects.create(slug="test-set", label="Test Set")
        cls.content_type = ContentType.objects.create(
            slug="static-page", label="Static Page", attribute_set=cls.attr_set
        )
        cls.ch_default = ContentChannel.objects.create(idx="default", name="Default", is_default=True)
        cls.ch_de = ContentChannel.objects.create(idx="de-market", name="DE Market")

    def _create_draft(self, channels=None):
        content = Content.objects.create(content={}, meta={})
        draft = Draft.objects.create(content_type=self.content_type, content=content, language=self.lang)
        if channels:
            draft.channels.set(channels)
        return draft

    def test_draft_no_channels_is_public(self):
        draft = self._create_draft()
        self.assertEqual(draft.channels.count(), 0)

    def test_draft_one_channel(self):
        draft = self._create_draft(channels=[self.ch_default])
        self.assertEqual(draft.channels.count(), 1)
        self.assertIn(self.ch_default, draft.channels.all())

    def test_draft_multiple_channels(self):
        draft = self._create_draft(channels=[self.ch_default, self.ch_de])
        self.assertEqual(draft.channels.count(), 2)

    def test_add_remove_channels(self):
        draft = self._create_draft()
        draft.channels.add(self.ch_default)
        self.assertEqual(draft.channels.count(), 1)
        draft.channels.remove(self.ch_default)
        self.assertEqual(draft.channels.count(), 0)

    def test_channel_reverse_relation(self):
        draft = self._create_draft(channels=[self.ch_default])
        self.assertIn(draft, self.ch_default.drafts.all())
