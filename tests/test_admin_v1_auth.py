# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Authentication contract of the v1 Admin API (`/api-admin/contentdb/v1/`).

Regression guard for 5.1.0: these views used to authenticate through `DjangoAuth`,
which called `django.contrib.auth.authenticate()` and therefore only worked when the
deploying service listed a JWT-reading backend in `AUTHENTICATION_BACKENDS`. Adopting
the module without that undocumented setting produced HTTP 401 on every admin request.

`tests/settings.py` deliberately configures ModelBackend only — the exact configuration
that used to fail. A real Bearer token must be enough on its own.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

ADMIN_ENDPOINTS = [
    "/api-admin/contentdb/v1/channels/",
    "/api-admin/contentdb/v1/languages/",
    "/api-admin/contentdb/v1/content-types/",
]


def bearer(user):
    return f"Bearer {RefreshToken.for_user(user).access_token}"


@pytest.mark.django_db
@pytest.mark.parametrize("url", ADMIN_ENDPOINTS)
def test_admin_v1_accepts_bearer_token_with_model_backend_only(api_client, admin_user, url):
    response = api_client.get(url, HTTP_AUTHORIZATION=bearer(admin_user))

    assert response.status_code == 200, f"{url} rejected a valid admin JWT: {response.status_code}"


@pytest.mark.django_db
@pytest.mark.parametrize("url", ADMIN_ENDPOINTS)
def test_admin_v1_rejects_anonymous(api_client, url):
    assert api_client.get(url).status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize("url", ADMIN_ENDPOINTS)
def test_admin_v1_rejects_garbage_token(api_client, url):
    assert api_client.get(url, HTTP_AUTHORIZATION="Bearer not-a-jwt").status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize("url", ADMIN_ENDPOINTS)
def test_admin_v1_rejects_non_admin_without_content_permission(api_client, regular_user, url):
    """Authentication succeeds; IsAdminUser | ContentTypePermission is what stops the request."""
    response = api_client.get(url, HTTP_AUTHORIZATION=bearer(regular_user))

    assert response.status_code == 403
