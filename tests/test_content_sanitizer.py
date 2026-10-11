# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Stored page HTML is sanitised on write: the allowlist, the JSON walk and the three write paths of the API."""

import pytest

from django_contentdb.models import AttributeSet, Content, ContentType, Language
from django_contentdb.services.content_service import sanitize_content, sanitize_html

EDITOR_HTML = (
    '<h2 style="text-align: center">Title</h2><p>Text with <strong>bold</strong>, <em>italic</em> &amp; '
    '<a href="https://example.com/a?b=1&amp;c=2" target="_blank" rel="noopener noreferrer">a link</a><br>'
    '<span style="color: rgb(10, 20, 30)" data-color="#fff">colour</span></p><ul><li>one</li></ul>'
    '<img src="/media/a.png" alt="A" width="100"><table><tbody><tr><td colspan="2" colwidth="120">x</td></tr>'
    "</tbody></table>"
)


def test_editor_markup_survives_unchanged():
    assert sanitize_html(EDITOR_HTML) == EDITOR_HTML


@pytest.mark.parametrize(
    ("dirty", "clean"),
    [
        ("<p>a</p><script>alert(1)</script>", "<p>a</p>"),
        ("<p>a</p><ScRiPt src=//evil.example></sCrIpT>b", "<p>a</p>b"),
        ("<p>a<script>alert(1)", "<p>a"),
        ("<style>p{background:url(//evil.example)}</style><p>a</p>", "<p>a</p>"),
        ('<img src="x.png" onerror="alert(1)">', '<img src="x.png">'),
        ('<p onclick="alert(1)" ONMOUSEOVER=alert(2)>a</p>', "<p>a</p>"),
        ('<a href="javascript:alert(1)">a</a>', "<a>a</a>"),
        ('<a href=" JaVa\tScRiPt:alert(1)">a</a>', "<a>a</a>"),
        ('<a href="jav&#x09;ascript:alert(1)">a</a>', "<a>a</a>"),
        ('<a href="&#106;avascript:alert(1)">a</a>', "<a>a</a>"),
        ('<a href="data:text/html;base64,PHNjcmlwdD4=">a</a>', "<a>a</a>"),
        ('<a href="vbscript:msgbox(1)">a</a>', "<a>a</a>"),
        ('<img src="data:image/svg+xml,<svg onload=alert(1)>">', "<img>"),
        ('<img src="javascript:alert(1)">', "<img>"),
        ('<iframe src="https://evil.example"></iframe><p>a</p>', "<p>a</p>"),
        ("<svg><a xlink:href='javascript:alert(1)'><text>x</text></a></svg>", "<a>x</a>"),
        ('<math><mtext><img src=x onerror="alert(1)"></mtext></math>', '<img src="x">'),
        ('<object data="x"></object><embed src="x"><form action="x"><input name="a"></form>', ""),
        ("<!-- c --><p>a</p><![CDATA[<script>]]><?php x ?>", "<p>a</p>"),
        ('<p style="position: fixed; top: 0; color: red; background-image: url(//evil.example/x)">a</p>', None),
        ('<a href="https://example.com" target="_blank">a</a>', None),
        ('<a href="mailto:shop@example.com">m</a><a href="/path#x">p</a><a href="#top">t</a>', None),
        ('<p title="&quot;><script>alert(1)</script>">a &lt;script&gt;alert(1)&lt;/script&gt; b</p>', None),
        ('<a href="/x" rel="nofollow sponsored">a</a>', '<a href="/x" rel="nofollow sponsored">a</a>'),
        (
            '<a href="/x" target="_blank" rel="opener">a</a>',
            '<a href="/x" target="_blank" rel="noopener noreferrer">a</a>',
        ),
        ("a < b & c > d", "a &lt; b &amp; c &gt; d"),
    ],
)
def test_dangerous_markup_is_removed(dirty, clean):
    expected = {
        '<p style="position: fixed; top: 0; color: red; background-image: url(//evil.example/x)">a</p>': (
            '<p style="color: red">a</p>'
        ),
        '<a href="https://example.com" target="_blank">a</a>': (
            '<a href="https://example.com" target="_blank" rel="noopener noreferrer">a</a>'
        ),
        '<a href="mailto:shop@example.com">m</a><a href="/path#x">p</a><a href="#top">t</a>': dirty,
        '<p title="&quot;><script>alert(1)</script>">a &lt;script&gt;alert(1)&lt;/script&gt; b</p>': (
            '<p title="&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;">a &lt;script&gt;alert(1)&lt;/script&gt; b</p>'
        ),
    }
    assert sanitize_html(dirty) == (clean if clean is not None else expected[dirty])


@pytest.mark.parametrize("html", [EDITOR_HTML, '<p onclick="x">a &amp; b<script>1</script></p>', "a < b"])
def test_sanitising_is_idempotent(html):
    once = sanitize_html(html)
    assert sanitize_html(once) == once


SCRIPT = "<script>alert(1)</script>"
DIRTY_CONTENT = {
    "sections_order": ["s1"],
    "tiles_order": ["t1"],
    "sections": {"s1": {"core_type": "section-text", "title": "Sale < 50% & more", "description": f"<p>s</p>{SCRIPT}"}},
    "tiles": {
        "t1": {
            "core_type": "tile-form",
            "description": '<p>t</p><img src=x onerror="alert(1)">',
            "header_area": '<a href="javascript:alert(1)">h</a>',
            "footer_area": f"<p>f</p>{SCRIPT}",
            "accordion_tile": [{"label": "Q", "wysiwyg": f"<p>a</p>{SCRIPT}"}],
            "consents": {"0": {"consent": '<p onmouseover="alert(1)">c</p>'}},
            "images_set": [{"url": "/media/a.png?w=1&h=2", "width": 100, "visible": True, "alt": None}],
        }
    },
}
CLEAN_CONTENT = {
    "sections_order": ["s1"],
    "tiles_order": ["t1"],
    "sections": {"s1": {"core_type": "section-text", "title": "Sale < 50% & more", "description": "<p>s</p>"}},
    "tiles": {
        "t1": {
            "core_type": "tile-form",
            "description": '<p>t</p><img src="x">',
            "header_area": "<a>h</a>",
            "footer_area": "<p>f</p>",
            "accordion_tile": [{"label": "Q", "wysiwyg": "<p>a</p>"}],
            "consents": {"0": {"consent": "<p>c</p>"}},
            "images_set": [{"url": "/media/a.png?w=1&h=2", "width": 100, "visible": True, "alt": None}],
        }
    },
}


def test_every_string_of_nested_content_json_is_sanitised_and_plain_text_is_kept():
    assert sanitize_content(DIRTY_CONTENT) == CLEAN_CONTENT
    assert sanitize_content(None) is None


@pytest.fixture
def static_page(db):
    Language.objects.create(iso2="EN", iso3="ENG")
    attribute_set = AttributeSet.objects.create(slug="test-set", label="Test Set")
    return ContentType.objects.create(slug="static-page", label="Static Page", attribute_set=attribute_set)


def _body(**overrides):
    body = {"name": "Page", "language": "EN", "routes": [], "attributes": {}, "meta": {}, "content": DIRTY_CONTENT}
    return {**body, "extension": None, **overrides}


URL = "/api-admin/contentdb/v1/content/static-page/"


@pytest.mark.django_db
def test_draft_create_update_and_publish_store_sanitised_html(admin_client, static_page):
    extension = {"lead": f"<p>l</p>{SCRIPT}"}
    created = admin_client.post(URL, _body(extension=extension), format="json")
    assert created.status_code == 201, created.content
    uid = created.json()["data"]["uid"]
    draft = Content.objects.get(uid=uid)
    assert draft.content == CLEAN_CONTENT
    assert draft.extension == {"lead": "<p>l</p>"}

    Content.objects.filter(uid=uid).update(content={})
    updated = admin_client.put(f"{URL}{uid}/", _body(), format="json")
    assert updated.status_code == 200, updated.content
    assert Content.objects.get(uid=uid).content == CLEAN_CONTENT

    published = admin_client.post(f"{URL}{uid}/published/", _body(extension=extension), format="json")
    assert published.status_code == 201, published.content
    snapshot = Content.objects.get(published__draft__content__uid=uid)
    assert snapshot.content == CLEAN_CONTENT
    assert snapshot.extension == {"lead": "<p>l</p>"}
