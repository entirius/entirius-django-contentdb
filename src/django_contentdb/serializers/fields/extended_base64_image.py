# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from drf_extra_fields.fields import Base64ImageField


class ExtendedBase64ImageField(Base64ImageField):
    ALLOWED_TYPES = ("jpeg", "jpg", "png", "gif", "webp")

    def to_internal_value(self, data):
        if data in (None, "", []) and not self.required:
            return None

        # Otherwise, use the parent's validation
        return super().to_internal_value(data)
