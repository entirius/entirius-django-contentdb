# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The router roots (an index of route names) declare their own classes: no credentials are evaluated there."""

import pytest
from rest_framework.permissions import AllowAny
from rest_framework.routers import APIRootView

from django_contentdb.urls import admin_router, public_router


@pytest.mark.parametrize("router", [public_router, admin_router], ids=["public", "admin"])
def test_router_root_declares_no_authentication(router):
    root = router.get_api_root_view().cls
    assert root is not APIRootView  # its own class, not the framework's, which inherits the service default
    assert root.authentication_classes == []
    assert root.permission_classes == [AllowAny]


def test_admin_root_keeps_its_access_area():
    assert admin_router.get_api_root_view().cls.access_area == "content.pages"
    assert not hasattr(public_router.get_api_root_view().cls, "access_area")
