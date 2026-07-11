# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class AttributeToSet(models.Model):
    attribute_set = models.ForeignKey("AttributeSet", on_delete=models.CASCADE)
    attribute = models.ForeignKey("Attribute", on_delete=models.CASCADE)
    objects = models.Manager()
