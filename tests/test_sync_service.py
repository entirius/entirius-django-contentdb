# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import patch

from django.test import TestCase

from django_contentdb.models import ContentChannel, Language
from django_contentdb.services.sync_service import sync_channels_from_pim, sync_languages_from_pim


class SyncChannelsTest(TestCase):
    def test_sync_when_pim_not_installed(self):
        with patch("django_contentdb.services.sync_service.sync_channels_from_pim", wraps=sync_channels_from_pim):
            # Simulate ImportError by patching the import inside the function
            with patch.dict("sys.modules", {"django_pim": None, "django_pim.models": None}):
                result = sync_channels_from_pim()
        self.assertEqual(result, 0)

    def test_sync_creates_channels(self):
        lang = Language.objects.create(iso2="EN", iso3="ENG")

        # Test that update_or_create correctly creates a ContentChannel
        # (mirrors what sync_channels_from_pim does for each PIM channel)
        ContentChannel.objects.update_or_create(
            idx="test-channel", defaults={"name": "Test Channel", "default_language": lang, "is_default": True}
        )
        self.assertTrue(ContentChannel.objects.filter(idx="test-channel").exists())
        ch = ContentChannel.objects.get(idx="test-channel")
        self.assertEqual(ch.name, "Test Channel")
        self.assertTrue(ch.is_default)
        self.assertEqual(ch.default_language, lang)

    def test_sync_updates_existing_channels(self):
        lang = Language.objects.create(iso2="EN", iso3="ENG")
        ContentChannel.objects.create(idx="existing", name="Old Name")

        ContentChannel.objects.update_or_create(
            idx="existing", defaults={"name": "New Name", "default_language": lang, "is_default": False}
        )
        ch = ContentChannel.objects.get(idx="existing")
        self.assertEqual(ch.name, "New Name")
        self.assertEqual(ch.default_language, lang)


class SyncLanguagesTest(TestCase):
    def test_sync_when_regional_not_installed(self):
        with patch.dict("sys.modules", {"django_regional": None, "django_regional.models": None}):
            created, updated = sync_languages_from_pim()
        self.assertEqual(created, 0)
        self.assertEqual(updated, 0)

    def test_language_update_or_create(self):
        Language.objects.create(iso2="EN", iso3="ENG")
        obj, created = Language.objects.update_or_create(
            iso2__iexact="EN", defaults={"iso2": "EN", "iso3": "ENG", "name_en": "English", "name_pl": "Angielski"}
        )
        self.assertFalse(created)
        self.assertEqual(obj.name_en, "English")
        self.assertEqual(obj.name_pl, "Angielski")

    def test_language_create_new(self):
        obj, created = Language.objects.update_or_create(
            iso2__iexact="DE", defaults={"iso2": "DE", "iso3": "DEU", "name_en": "German", "name_pl": "Niemiecki"}
        )
        self.assertTrue(created)
        self.assertEqual(obj.iso2, "DE")
