# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand

from django_contentdb.models import ContentChannel, Draft


class Command(BaseCommand):
    help = "Assign channels to Drafts that have no channel assignments (currently public)"

    def add_arguments(self, parser):
        parser.add_argument("--channel", type=str, help="Assign only this channel (by idx)")
        parser.add_argument("--all", action="store_true", help="Assign all existing ContentChannels")

    def handle(self, *args, **options):
        drafts = Draft.objects.filter(channels__isnull=True).distinct()
        draft_count = drafts.count()

        if draft_count == 0:
            self.stdout.write(self.style.WARNING("No drafts with empty channels found"))
            return

        if options["channel"]:
            try:
                channel = ContentChannel.objects.get(idx=options["channel"])
            except ContentChannel.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Channel '{options['channel']}' not found"))
                return
            channels = [channel]
        elif options["all"]:
            channels = list(ContentChannel.objects.all())
        else:
            self.stdout.write(self.style.ERROR("Specify --channel=idx or --all"))
            return

        if not channels:
            self.stdout.write(self.style.WARNING("No ContentChannels exist"))
            return

        through = Draft.channels.through
        rows = [through(draft_id=d.pk, contentchannel_id=ch.pk) for d in drafts for ch in channels]
        through.objects.bulk_create(rows, ignore_conflicts=True, batch_size=500)

        channel_names = ", ".join(c.idx for c in channels)
        self.stdout.write(self.style.SUCCESS(f"Assigned [{channel_names}] to {draft_count} drafts"))
