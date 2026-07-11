# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.apps import AppConfig


class ContentdbConfig(AppConfig):
    name = "django_contentdb"
    verbose_name = "Content Database"
    is_volkanos = True

    def ready(self):
        # Implicitly connect all signal handlers decorated with @receiver.
        pass
