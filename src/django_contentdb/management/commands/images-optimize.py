# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from django.core.management.base import BaseCommand

from django_contentdb.models import Image
from django_contentdb.tasks import optimize_image

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Optimize/Re-optimize all images"

    def handle(self, *args, **options):
        images = Image.objects.all()
        succ = 0
        failed = 0
        for instance in images:
            try:
                optimize_image(instance.pk)
                succ = succ + 1
            except Exception as e:
                failed = failed + 1
                logger.error(f"COMMAND images-optimize failed on image {instance}: {e}")

        style = self.style.SUCCESS if failed == 0 else self.style.ERROR
        self.stdout.write(style(f"Finished working, {succ} done, {failed} failed"))
