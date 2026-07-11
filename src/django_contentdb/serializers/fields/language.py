# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers


class LanguageField(serializers.Field):
    def to_representation(self, value):
        if value.contentset_set.exists():
            result = value.contentset_set.filter(drafttocontentset__draft=value).values_list(
                "drafttocontentset__draft__language__iso2", flat=True
            )[0]
            return result
        else:
            return None
