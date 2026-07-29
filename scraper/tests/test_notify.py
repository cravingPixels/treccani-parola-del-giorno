from datetime import datetime
from zoneinfo import ZoneInfo

from scrape import latest_stored_word, should_post

ROME = ZoneInfo("Europe/Rome")


def at(hour):
    return datetime(2026, 7, 17, hour, 20, tzinfo=ROME)


def test_latest_stored_word_empty():
    assert latest_stored_word({"words": []}) is None


def test_latest_stored_word_picks_most_recent_date():
    store = {"words": [
        {"date": "2026-07-16", "word": "vecchia"},
        {"date": "2026-07-17", "word": "nuova"},
    ]}
    assert latest_stored_word(store) == "nuova"


def test_no_post_before_post_hour():
    assert should_post(at(7), 9, has_today_word=True, last_posted_date=None) is False


def test_posts_at_or_after_post_hour_when_fresh_word_present():
    assert should_post(at(9), 9, has_today_word=True, last_posted_date=None) is True
    assert should_post(at(11), 9, has_today_word=True, last_posted_date=None) is True


def test_no_post_when_no_fresh_word_yet():
    # e.g. weekend: Treccani didn't roll over, so nothing captured for today.
    assert should_post(at(10), 9, has_today_word=False, last_posted_date=None) is False


def test_no_double_post_same_day():
    assert should_post(at(10), 9, has_today_word=True, last_posted_date="2026-07-17") is False


def test_force_bypasses_hour_gate_but_not_freshness():
    assert should_post(at(6), 9, has_today_word=True, last_posted_date=None, force=True) is True
    # force still won't invent a post when there is no fresh word
    assert should_post(at(6), 9, has_today_word=False, last_posted_date=None, force=True) is False


def test_configurable_post_hour():
    assert should_post(at(11), 12, has_today_word=True, last_posted_date=None) is False
    assert should_post(at(12), 12, has_today_word=True, last_posted_date=None) is True
