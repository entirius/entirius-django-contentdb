# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand

from django_contentdb.services.sync_service import sync_channels_from_pim


class Command(BaseCommand):
    help = "Sync ContentChannels from PIM Channel model"

    def handle(self, *args, **options):
        count = sync_channels_from_pim()
        style = self.style.SUCCESS if count > 0 else self.style.WARNING
        self.stdout.write(style(f"Synced {count} channels from PIM"))
