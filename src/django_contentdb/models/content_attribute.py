# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class ContentAttribute(models.Model):
    content = models.ForeignKey("Content", on_delete=models.CASCADE)
    attribute_value = models.ForeignKey("AttributeValue", on_delete=models.CASCADE)
    objects = models.Manager()
