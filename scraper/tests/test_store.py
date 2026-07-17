import json

from scrape import WordOfDay, load_store, save_store, upsert_word

ENTRY = WordOfDay(
    date="2026-07-17", word="eteròclito", slug="eteroclito",
    url="https://www.treccani.it/vocabolario/eteroclito/", definition=None,
)


def test_upsert_appends_new_date():
    store = {"words": []}
    assert upsert_word(store, ENTRY) is True
    assert len(store["words"]) == 1
    assert store["words"][0]["word"] == "eteròclito"


def test_upsert_is_idempotent_for_same_date():
    store = {"words": []}
    upsert_word(store, ENTRY)
    added_again = upsert_word(store, ENTRY)
    assert added_again is False
    assert len(store["words"]) == 1


def test_store_roundtrip_preserves_utf8(tmp_path):
    path = tmp_path / "words.json"
    store = {"words": []}
    upsert_word(store, ENTRY)
    save_store(store, path)
    raw = path.read_text(encoding="utf-8")
    assert "eteròclito" in raw  # accents not escaped
    assert load_store(path)["words"][0]["date"] == "2026-07-17"
    json.loads(raw)  # valid JSON


def test_words_kept_sorted_by_date():
    store = {"words": []}
    later = WordOfDay(date="2026-07-18", word="b", slug="b", url="u", definition=None)
    upsert_word(store, later)
    upsert_word(store, ENTRY)  # earlier date
    assert [w["date"] for w in store["words"]] == ["2026-07-17", "2026-07-18"]
