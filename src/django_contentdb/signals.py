# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db.models.signals import pre_delete
from django.dispatch import receiver

from django_contentdb.models import Image, Thumbnail


@receiver(pre_delete, sender=Image, dispatch_uid="image_post_delete_handler")
def image_pre_delete_handler(sender, instance, using, *args, **kwargs):
    # Get thumbnails for Image being deleted
    to_delete = Thumbnail.objects.filter(source=instance)
    for elem in to_delete:
        elem.delete()
