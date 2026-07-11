# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import factory
from django.test import TestCase

from django_contentdb.models import ContentChannel, Language


class LanguageFactory(factory.django.DjangoModelFactory):
    iso2 = factory.Sequence(lambda n: f"L{n}"[:2])
    iso3 = factory.Sequence(lambda n: f"LN{n}"[:3])

    class Meta:
        model = Language


class ContentChannelFactory(factory.django.DjangoModelFactory):
    idx = factory.Sequence(lambda n: f"channel-{n}")
    name = factory.LazyAttribute(lambda o: f"Channel {o.idx}")
    is_default = False

    class Meta:
        model = ContentChannel


class ContentChannelModelTest(TestCase):
    def test_create_channel(self):
        channel = ContentChannel.objects.create(idx="default", name="Default Channel")
        self.assertEqual(channel.idx, "default")
        self.assertEqual(channel.name, "Default Channel")
        self.assertFalse(channel.is_default)
        self.assertIsNone(channel.default_language)

    def test_idx_unique(self):
        ContentChannel.objects.create(idx="unique-ch")
        with self.assertRaises(Exception):
            ContentChannel.objects.create(idx="unique-ch")

    def test_is_default_enforcement(self):
        ch1 = ContentChannel.objects.create(idx="ch1", is_default=True)
        ch2 = ContentChannel.objects.create(idx="ch2", is_default=True)
        ch1.refresh_from_db()
        self.assertFalse(ch1.is_default)
        self.assertTrue(ch2.is_default)

    def test_default_language_set_null(self):
        lang = Language.objects.create(iso2="EN", iso3="ENG")
        channel = ContentChannel.objects.create(idx="ch-lang", default_language=lang)
        lang.delete()
        channel.refresh_from_db()
        self.assertIsNone(channel.default_language)

    def test_str(self):
        channel = ContentChannel.objects.create(idx="test-str")
        self.assertEqual(str(channel), "test-str")


class LanguageEnrichedTest(TestCase):
    def test_name_fields(self):
        lang = Language.objects.create(iso2="EN", iso3="ENG", name_en="English", name_pl="Angielski")
        self.assertEqual(lang.name_en, "English")
        self.assertEqual(lang.name_pl, "Angielski")

    def test_name_fields_default_empty(self):
        lang = Language.objects.create(iso2="FR", iso3="FRA")
        self.assertEqual(lang.name_en, "")
        self.assertEqual(lang.name_pl, "")
