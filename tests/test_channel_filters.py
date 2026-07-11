# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.test import TestCase

from django_contentdb.models import AttributeSet, Content, ContentChannel, ContentType, Draft, Language, Published


class ChannelFilterTest(TestCase):
    """Test the channel filter logic on Published content querysets."""

    @classmethod
    def setUpTestData(cls):
        cls.lang = Language.objects.create(iso2="EN", iso3="ENG")
        cls.attr_set = AttributeSet.objects.create(slug="test-set", label="Test Set")
        cls.ct = ContentType.objects.create(slug="static-page", label="Static Page", attribute_set=cls.attr_set)
        cls.ch_default = ContentChannel.objects.create(idx="default", name="Default", is_default=True)
        cls.ch_de = ContentChannel.objects.create(idx="de-market", name="DE Market")

        # Public content (no channels)
        cls.public_draft, cls.public_published = cls._create_published()

        # Default-only content
        cls.default_draft, cls.default_published = cls._create_published(channels=[cls.ch_default])

        # Multi-channel content
        cls.multi_draft, cls.multi_published = cls._create_published(channels=[cls.ch_default, cls.ch_de])

        # DE-only content
        cls.de_draft, cls.de_published = cls._create_published(channels=[cls.ch_de])

    @classmethod
    def _create_published(cls, channels=None):
        draft_content = Content.objects.create(content={}, meta={})
        draft = Draft.objects.create(content_type=cls.ct, content=draft_content, language=cls.lang)
        if channels:
            draft.channels.set(channels)

        pub_content = Content.objects.create(content={}, meta={})
        published = Published.objects.create(draft=draft, content=pub_content)
        return draft, published

    def _filter_by_channel(self, channel_idx):
        """Simulate the channel filter logic from PublishedFilter."""
        from django.db.models import Q

        return (
            Content.objects.filter(published__isnull=False)
            .filter(Q(published__draft__channels__idx=channel_idx) | Q(published__draft__channels__isnull=True))
            .distinct()
        )

    def test_channel_default_returns_public_and_default(self):
        results = self._filter_by_channel("default")
        result_pks = set(results.values_list("pk", flat=True))
        # Should include: public (no channels), default-only, multi-channel
        self.assertIn(self.public_published.content.pk, result_pks)
        self.assertIn(self.default_published.content.pk, result_pks)
        self.assertIn(self.multi_published.content.pk, result_pks)
        # Should NOT include: de-only
        self.assertNotIn(self.de_published.content.pk, result_pks)

    def test_channel_de_returns_public_and_de(self):
        results = self._filter_by_channel("de-market")
        result_pks = set(results.values_list("pk", flat=True))
        # Should include: public, multi-channel, de-only
        self.assertIn(self.public_published.content.pk, result_pks)
        self.assertIn(self.multi_published.content.pk, result_pks)
        self.assertIn(self.de_published.content.pk, result_pks)
        # Should NOT include: default-only
        self.assertNotIn(self.default_published.content.pk, result_pks)

    def test_channel_nonexistent_returns_only_public(self):
        results = self._filter_by_channel("nonexistent")
        result_pks = set(results.values_list("pk", flat=True))
        # Only public content (no channels assigned)
        self.assertIn(self.public_published.content.pk, result_pks)
        self.assertNotIn(self.default_published.content.pk, result_pks)

    def test_no_channel_filter_returns_all(self):
        results = Content.objects.filter(published__isnull=False)
        self.assertEqual(results.count(), 4)
