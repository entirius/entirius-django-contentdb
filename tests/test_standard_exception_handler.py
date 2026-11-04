# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""standard_exception_handler (the v1 envelope) keeps the status and headers DRF's handler sets."""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView
from rest_framework.views import exception_handler as drf_exception_handler

from django_contentdb.utils import standard_exception_handler

V1_PATH = "/api/contentdb/v1/x/"


class _BasicAuthView(APIView):
    """First authenticator has authenticate_header: DRF answers 401 with WWW-Authenticate."""

    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get_exception_handler(self):
        return standard_exception_handler

    def get(self, request):
        return Response({})


class _SessionAuthView(_BasicAuthView):
    """First authenticator has no authenticate_header: DRF turns the 401 into a 403."""

    authentication_classes = [SessionAuthentication]


class _SlowDown(BaseThrottle):
    def allow_request(self, request, view):
        return False

    def wait(self):
        return 2.3


class _ThrottledView(_BasicAuthView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [_SlowDown]


def _get(view, **headers):
    return view.as_view()(APIRequestFactory().get(V1_PATH, **headers))


def _handle(exc):
    return standard_exception_handler(exc, {"request": APIRequestFactory().get(V1_PATH)})


def test_missing_credentials_keep_www_authenticate():
    response = _get(_BasicAuthView)

    assert response.status_code == 401
    assert response.data["meta"]["status"] == "UNAUTHORIZED"
    assert response["WWW-Authenticate"] == 'Basic realm="api"'


def test_failed_authentication_keeps_www_authenticate():
    response = _get(_BasicAuthView, HTTP_AUTHORIZATION="Basic not-base64!")

    assert response.status_code == 401
    assert response.data["meta"]["status"] == "UNAUTHORIZED"
    assert response["WWW-Authenticate"] == 'Basic realm="api"'


def test_authenticator_without_header_stays_a_403():
    response = _get(_SessionAuthView)

    assert response.status_code == 403
    assert response.data["meta"]["status"] == "FORBIDDEN"
    assert "WWW-Authenticate" not in response


def test_throttled_keeps_drf_retry_after():
    response = _get(_ThrottledView)

    assert response.status_code == 429
    assert response.data["meta"]["status_code"] == 429
    drf_response = drf_exception_handler(Throttled(wait=2.3), {})
    assert response["Retry-After"] == drf_response["Retry-After"] == "3"


def test_throttled_without_wait_has_no_retry_after():
    response = _handle(Throttled())

    assert response.status_code == 429
    assert "Retry-After" not in response


def test_validation_error_adds_no_headers():
    response = _handle(ValidationError({"url": ["This field is required."]}))

    assert response.status_code == 400
    assert response.data["data"] == {"url": ["This field is required."]}
    assert set(response.headers) == set(Response().headers)


def test_django_http404_is_a_404():
    """get_object() and get_object_or_404 raise Django's Http404, which has no get_codes()."""
    response = _handle(Http404("No Language matches the given query."))

    assert response.status_code == 404
    assert response.data["meta"] == {"status": "NOT_FOUND", "status_code": 404, "message": "not_found"}
    assert response.data["data"] == {"detail": "No Language matches the given query."}


def test_django_permission_denied_is_a_403():
    response = _handle(PermissionDenied())

    assert response.status_code == 403
    assert response.data["meta"]["status"] == "FORBIDDEN"
    assert response.data["meta"]["message"] == "permission_denied"
