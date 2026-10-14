# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The article converter port. Golden files under `fixtures/article_converter/` were produced by the original
converter from the `.md` next to them (section uids replaced by their position)."""

import json
import re
from pathlib import Path

import pytest

from django_contentdb.services.article_converter import DEFAULT_FAQ_TITLE, build_payload

FIXTURES = Path(__file__).parent / "fixtures" / "article_converter"
GOLDEN_META = {
    "reference-article": {"lang": "pl", "seo_title": "Product data ready for automation"},
    "short-article": {"lang": "pl", "seo_description": "A short note.", "og_title": "Short"},
}
KNOWN_TYPES = {"section-text", "section-faq"}


def sections(payload: dict) -> list[dict]:
    return [payload["content"]["sections"][uid] for uid in payload["content"]["sections_order"]]


def text_html(payload: dict) -> str:
    return "".join(s.get("description", "") for s in sections(payload) if s["core_type"] == "section-text")


def comparable(payload: dict) -> dict:
    content = {**payload["content"], "sections": sections(payload)}
    content["sections_order"] = list(range(len(content["sections"])))
    return {key: payload[key] for key in ("name", "language", "meta", "extension")} | {"content": content}


@pytest.mark.parametrize("name", sorted(GOLDEN_META))
def test_parity_with_the_original_converter(name):
    payload = build_payload((FIXTURES / f"{name}.md").read_text(), GOLDEN_META[name], slug="")
    assert comparable(payload) == json.loads((FIXTURES / f"{name}.golden.json").read_text())


def reference() -> dict:
    return build_payload((FIXTURES / "reference-article.md").read_text(), {"lang": "en"}, slug="ref")


def test_headings_preserved_in_order():
    headings = re.findall(r"<h[23]>(.*?)</h[23]>", text_html(reference()))
    assert headings == [
        "Start with an attribute audit",
        "Agree on one source of truth",
        "Keep the review short",
        "Automate the boring parts",
    ]


def test_meta_has_seven_keys_and_capped_description():
    payload = reference()
    assert set(payload["meta"]) == {"index", "follow", "title", "description", "og_title", "og_description", "og_image"}
    assert len(payload["meta"]["description"]) <= 160
    assert payload["routes"] == ["ref"]


def test_only_known_core_types_and_no_tiles():
    content = reference()["content"]
    assert {s["core_type"] for s in content["sections"].values()} <= KNOWN_TYPES
    assert set(content["sections_order"]) == set(content["sections"])
    assert content["tiles"] == {} and content["tiles_order"] == {}


def test_image_ends_a_text_section_and_hero_is_dropped():
    md = "# T\n\n![hero](http://x/0.png)\n\n## A\n\nText A.\n\n![one](http://x/1.png)\n\n## B\n\nText B.\n"
    payload = build_payload(md, {"lang": "en"}, slug="t")
    assert [s["core_type"] for s in sections(payload)] == ["section-text", "section-text"]
    assert "img" not in text_html(payload)


def test_table_and_list_render():
    md = "# T\n\n## S\n\n- item one\n- item two\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    html = text_html(build_payload(md, {"lang": "en"}, slug="t"))
    assert "<ul><li><p>item one</p></li>" in html
    assert "<table>" in html and "<th>A</th>" in html and "<td>1</td>" in html


@pytest.mark.parametrize("heading", ["FAQ", "FAQs", "Frequently asked questions", "Na jakie pytania znajdziesz?"])
def test_faq_heading_variants(heading):
    md = f"# T\n\n## Section\n\nText.\n\n## {heading}\n\n### First question?\nAnswer.\n"
    faq = [s for s in sections(build_payload(md, {"lang": "en"}, slug="t")) if s["core_type"] == "section-faq"]
    assert faq and faq[0]["faq_items"][0]["question"] == "First question?"


def test_faq_title_follows_the_language():
    md = "# T\n\n## FAQ\n\n### Q?\n\nA.\n"
    assert sections(build_payload(md, {"lang": "en"}, slug=""))[-1]["title"] == DEFAULT_FAQ_TITLE
    assert sections(build_payload(md, {"lang": "pl"}, slug=""))[-1]["title"].startswith("Na jakie pytania")


def test_spacer_rhythm():
    md = "# T\n\n## Section\n\nText.\n\n- a\n- b\n\n## Second\n\nText 2.\n"
    html = text_html(build_payload(md, {"lang": "en"}, slug="t"))
    assert "</h2><p></p>" in html
    assert "</ul><p></p><h2>" in html


def test_description_falls_back_to_the_first_paragraph():
    md = "# T\n\n" + "word " * 60 + "\n"
    payload = build_payload(md, {"lang": "en"}, slug="t")
    assert payload["meta"]["description"].endswith("…") and len(payload["meta"]["description"]) == 158
    assert payload["extension"]["description"] == payload["meta"]["description"]
