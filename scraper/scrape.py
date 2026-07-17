#!/usr/bin/env python3
"""Scrape Treccani's "Parola del giorno", store it, and post it to Slack.

Design notes:
- We anchor extraction on the visible label element text "Parola del giorno"
  and take the following <h5>. Treccani's CSS classes are emotion-hashed and
  change on every rebuild, so they are NOT used as selectors.
- The homepage repeats the string "Parola del giorno" inside a Next.js JSON
  hydration blob; we therefore match a real DOM *element*, never a substring.
- Fail loudly: any anomaly raises ScrapeError so the workflow goes red and (if
  a webhook is configured) posts a distinct alert, instead of posting a blank.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

HOME_URL = "https://www.treccani.it/"
BASE_URL = "https://www.treccani.it"
LABEL_TEXT = "Parola del giorno"
ROME = ZoneInfo("Europe/Rome")
TARGET_LOCAL_HOUR = 9

# Honest, identifiable User-Agent (good-faith scraping; Treccani logs spoofed UAs).
USER_AGENT = (
    "treccani-parola-del-giorno-bot/1.0 "
    "(+https://github.com/cravingPixels/treccani-parola-del-giorno; personal use, 1 req/day)"
)

DATA_FILE = Path(__file__).resolve().parent.parent / "docs" / "data" / "words.json"

# A Treccani lemma: letters incl. accented, spaces, apostrophes, hyphens.
WORD_RE = re.compile(r"^[\wàáèéìíòóùúäöüç'\- ]{1,60}$", re.UNICODE)


class ScrapeError(RuntimeError):
    """Raised when the homepage does not look the way we expect."""


@dataclass(frozen=True)
class WordOfDay:
    date: str
    word: str
    slug: str
    url: str
    definition: str | None = None


def parse_word_of_day(html: str) -> tuple[str, str]:
    """Return (word, slug) from the homepage HTML. Raise ScrapeError on anomaly."""
    soup = BeautifulSoup(html, "html.parser")

    label = soup.find(
        lambda tag: tag.name in ("span", "p", "div")
        and tag.get_text(strip=True) == LABEL_TEXT
    )
    if label is None:
        raise ScrapeError(f"Label element {LABEL_TEXT!r} not found in homepage")

    heading = label.find_next("h5")
    if heading is None:
        raise ScrapeError("No <h5> found after the label element")

    word = heading.get_text(strip=True)
    if not word:
        raise ScrapeError("Word heading is empty")
    if not WORD_RE.match(word):
        raise ScrapeError(f"Extracted word failed sanity check: {word!r}")

    anchor = label.find_parent("a", href=True)
    if anchor is None:
        raise ScrapeError("No enclosing <a href> around the word-of-day card")

    m = re.search(r"/vocabolario/([^/]+)/?", anchor["href"])
    if not m:
        raise ScrapeError(f"Definition href not a /vocabolario/ link: {anchor['href']!r}")

    return word, m.group(1)


def parse_definition(html: str) -> str | None:
    """Best-effort short definition from a /vocabolario/<slug>/ page.

    Returns the first meaningful sentence, or None. Never raises — the daily
    post must survive a definition-extraction failure.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        for style in soup.find_all("style"):
            style.decompose()
        body = soup.find("article") or soup.find("main") or soup.body
        if body is None:
            return None
        text = re.sub(r"\s+", " ", body.get_text(" ", strip=True))
        # The entry text starts after the lemma/etymology; grab the first sense.
        text = text.split(" – ", 1)[-1] if " – " in text else text
        snippet = text.strip()[:280]
        return snippet or None
    except Exception:  # noqa: BLE001 - best effort by design
        return None


def fetch(url: str, timeout: int = 20) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    if resp.status_code != 200:
        raise ScrapeError(f"GET {url} returned HTTP {resp.status_code}")
    resp.encoding = "utf-8"
    return resp.text


def load_store(path: Path) -> dict:
    if not path.exists():
        return {"words": []}
    return json.loads(path.read_text(encoding="utf-8"))


def upsert_word(store: dict, entry: WordOfDay) -> bool:
    """Append entry unless its date already exists. Return True if added."""
    if any(w["date"] == entry.date for w in store["words"]):
        return False
    store["words"].append(asdict(entry))
    store["words"].sort(key=lambda w: w["date"])
    return True


def save_store(store: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_blocks(entry: WordOfDay) -> dict:
    lines = [f"*<{entry.url}|{entry.word}>*"]
    if entry.definition:
        lines.append(entry.definition)
    return {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "📖 Parola del giorno", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Treccani · {entry.date}"}]},
        ]
    }


def build_alert_blocks(message: str) -> dict:
    return {
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f":warning: *Parola del giorno — scrape failed*\n```{message}```"}}
        ]
    }


def post_to_slack(webhook_url: str, payload: dict, timeout: int = 15) -> None:
    resp = requests.post(webhook_url, json=payload, timeout=timeout)
    if resp.status_code != 200:
        raise ScrapeError(f"Slack webhook returned HTTP {resp.status_code}: {resp.text}")


def should_run_now(now: datetime | None = None) -> bool:
    now = now or datetime.now(ROME)
    return now.hour == TARGET_LOCAL_HOUR


def run(webhook_url: str | None, dry_run: bool, force: bool) -> int:
    if not force and not should_run_now():
        print(f"Not the {TARGET_LOCAL_HOUR}:00 Europe/Rome slot; skipping.")
        return 0

    today = datetime.now(ROME).strftime("%Y-%m-%d")
    try:
        word, slug = parse_word_of_day(fetch(HOME_URL))
        url = f"{BASE_URL}/vocabolario/{slug}/"
        definition = parse_definition(fetch(url))
        entry = WordOfDay(date=today, word=word, slug=slug, url=url, definition=definition)
    except ScrapeError as err:
        print(f"SCRAPE FAILED: {err}", file=sys.stderr)
        if webhook_url and not dry_run:
            post_to_slack(webhook_url, build_alert_blocks(str(err)))
        return 1

    store = load_store(DATA_FILE)
    added = upsert_word(store, entry)
    save_store(store, DATA_FILE)
    print(f"Word: {entry.word} ({entry.url}) — {'stored' if added else 'already stored'}")

    payload = build_blocks(entry)
    if dry_run or not webhook_url:
        print("DRY-RUN — Slack payload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        post_to_slack(webhook_url, payload)
        print("Posted to Slack.")
    return 0


def main(argv: list[str] | None = None) -> int:
    import os

    parser = argparse.ArgumentParser(description="Treccani parola del giorno → Slack")
    parser.add_argument("--dry-run", action="store_true", help="print payload, do not post")
    parser.add_argument("--force", action="store_true", help="ignore the 9am Europe/Rome guard")
    args = parser.parse_args(argv)
    return run(os.environ.get("SLACK_WEBHOOK_URL"), args.dry_run, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
