# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand

from django_contentdb.services.sync_service import sync_languages_from_pim


class Command(BaseCommand):
    help = "Sync ContentDB Languages from django_regional (PIM channel languages by default)"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Sync all regional languages, not just PIM channel ones")

    def handle(self, *args, **options):
        created, updated = sync_languages_from_pim(sync_all=options["all"])
        total = created + updated
        style = self.style.SUCCESS if total > 0 else self.style.WARNING
        self.stdout.write(style(f"Synced {total} languages ({created} created, {updated} updated)"))
