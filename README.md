# 📖 Parola del giorno → Slack

> Every morning, the Italian **word of the day** from [Treccani](https://www.treccani.it/)
> lands in a Slack channel — and every word is kept in a searchable public archive.

A tiny, fully **serverless and zero-cost** project: no server to run, no database to
pay for, no paid tier anywhere. It runs entirely on GitHub Actions and GitHub Pages.

**Live archive:** https://cravingpixels.github.io/treccani-parola-del-giorno/

---

## What it does

- 🕘 **Posts a daily word to Slack** at ~9:00 (Italy time) with its Treccani link and a short definition.
- 🗄️ **Archives every word** so you can look up *"what was the word on 15 July?"* at any time.
- 🔎 **Browsable history** — a small static page with instant client-side search by word or date.

## How it works

```
      GitHub Actions (daily cron)
                 │
                 ▼
        scraper/scrape.py
        ├─► Slack Incoming Webhook ......... the morning message
        └─► docs/data/words.json ........... the archive (committed back to the repo)
                 │
                 ▼
        GitHub Pages (docs/index.html) ..... searchable history site
```

1. A scheduled workflow runs the Python scraper each morning.
2. The scraper reads Treccani's homepage, extracts the word + a definition snippet,
   appends it to `docs/data/words.json`, and posts the message to Slack.
3. The updated archive is committed back to the repo; GitHub Pages serves it as a
   searchable web page — no backend involved.

## Why it costs nothing

| Piece            | Runs on                        | Cost |
|------------------|--------------------------------|------|
| Daily job        | GitHub Actions (public repo)   | free, unlimited minutes |
| Archive storage  | a JSON file in the repo        | free |
| History website  | GitHub Pages                   | free |
| Slack delivery    | Incoming Webhook               | free |

A couple of nice side effects of this design: the daily commit keeps the scheduled
workflow from being auto-disabled for inactivity, and the two cron times
(`07:17` + `08:17` UTC) with an `Europe/Rome` guard make the 9 AM post correct across
daylight-saving changes.

## Reliability

The scraper is deliberately defensive. It anchors on Treccani's visible
**"Parola del giorno"** element rather than fragile CSS class names, sanity-checks
the extracted word, and **fails loudly** — posting a distinct alert to Slack instead
of ever publishing a blank or wrong word. The definition snippet is best-effort: if
it can't be extracted, the word and link are still posted.

## Setup

### 1. Connect Slack

You need permission to install an app into your Slack workspace. (No admin rights?
Spin up a **free personal Slack workspace** — you're the admin there — and test with that.)

1. Go to <https://api.slack.com/apps> → **Create New App** → **From an app manifest**,
   and paste [`slack-app-manifest.yaml`](slack-app-manifest.yaml).
2. Enable **Incoming Webhooks**, add one to your target channel, and copy the URL.
3. Store it as a repository secret:
   ```bash
   gh secret set SLACK_WEBHOOK_URL
   ```

### 2. Enable GitHub Pages

Settings → **Pages** → Source: `main` branch, `/docs` folder.

### 3. Done

The daily schedule is already active. To post immediately:

```bash
gh workflow run daily.yml -f force=true
```

## Local development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r scraper/requirements.txt pytest

cd scraper && python -m pytest        # run the tests
python scrape.py --dry-run --force    # scrape and print the Slack payload without posting
```

- `--dry-run` prints the [Block Kit](https://app.slack.com/block-kit-builder) payload
  instead of sending it (works with no webhook configured).
- `--force` bypasses the "only at 9 AM Italy time" guard, for testing at any hour.

## Project layout

```
.github/workflows/daily.yml   # the scheduled scrape → post → commit job
.github/workflows/test.yml    # runs the tests on every push / PR
scraper/scrape.py             # fetch, parse, store, post
scraper/tests/                # parser + storage tests (with a saved homepage fixture)
docs/index.html               # the searchable history site (GitHub Pages)
docs/data/words.json          # the archive
slack-app-manifest.yaml       # one-click Slack app definition
```

## A note on scraping & copyright

Treccani doesn't offer a word-of-the-day API, so this reads the public homepage
**once per day** with an honest, identifiable User-Agent and stores only a short
definition snippet. It's intended for **personal, non-commercial** use. Please keep
usage minimal and respect Treccani's terms — the daily word and its definitions are
their copyrighted content.
