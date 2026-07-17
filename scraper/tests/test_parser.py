from pathlib import Path

import pytest

from scrape import ScrapeError, build_blocks, parse_word_of_day, WordOfDay

FIXTURE = Path(__file__).parent / "fixtures" / "treccani_home.html"


def test_parses_word_and_slug_from_real_homepage():
    html = FIXTURE.read_text(encoding="utf-8")
    word, slug = parse_word_of_day(html)
    assert word == "eteròclito"
    assert slug == "eteroclito"


def test_missing_label_raises():
    with pytest.raises(ScrapeError):
        parse_word_of_day("<html><body><h5>eteròclito</h5></body></html>")


def test_label_only_in_json_blob_is_ignored():
    # The label as a JSON string (not a DOM element) must NOT be matched.
    html = '<html><body><script>{"label":"Parola del giorno"}</script></body></html>'
    with pytest.raises(ScrapeError):
        parse_word_of_day(html)


def test_empty_heading_raises():
    html = '<a href="/vocabolario/x/"><span>Parola del giorno</span><h5></h5></a>'
    with pytest.raises(ScrapeError):
        parse_word_of_day(html)


def test_non_vocabolario_link_raises():
    html = '<a href="/enciclopedia/x/"><span>Parola del giorno</span><h5>ciao</h5></a>'
    with pytest.raises(ScrapeError):
        parse_word_of_day(html)


def test_build_blocks_includes_word_link_and_definition():
    entry = WordOfDay(
        date="2026-07-17", word="eteròclito", slug="eteroclito",
        url="https://www.treccani.it/vocabolario/eteroclito/", definition="Che si discosta.",
    )
    payload = build_blocks(entry)
    text = payload["blocks"][1]["text"]["text"]
    assert entry.url in text
    assert "eteròclito" in text
    assert "Che si discosta." in text
