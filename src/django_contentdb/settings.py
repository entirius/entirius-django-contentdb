# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

ADMIN_BASE_URL = getattr(settings, "API_ADMIN_BASE_URL", "/api-admin/").strip("/")
PUBLIC_BASE_URL = getattr(settings, "API_PUBLIC_BASE_URL", "/api/").strip("/")

THUMBNAIL_QUALITY = getattr(settings, "CONTENTDB_THUMBNAIL_QUALITY", 60)

CONTENTDB_IMAGE_MAX_WIDTH = getattr(settings, "CONTENTDB_IMAGE_MAX_WIDTH", 2560)
