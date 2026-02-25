from __future__ import annotations

from hal.extract_dom import extract_dom_content, should_use_vision


def test_short_text_switches_to_vision():
    html = "<html><body><p>tiny</p></body></html>"
    dom = extract_dom_content(html, "t", "tiny")
    assert should_use_vision(dom) is True


def test_long_article_keeps_dom():
    long_text = " ".join(["This is meaningful content."] * 120)
    html = f"<html><body><article><h1>Story</h1><p>{long_text}</p></article></body></html>"
    dom = extract_dom_content(html, "Story", long_text)
    assert len(dom.text_markdown) > 800
    assert should_use_vision(dom) is False
