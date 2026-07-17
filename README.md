# Parola del giorno → Slack

Posts Treccani's **Parola del giorno** to a Slack channel every morning (~9am Italy
time) and keeps a searchable history — all at **zero cost** on GitHub Actions +
GitHub Pages. No server, no database, no paid tier.

## How it works

```
GitHub Actions cron ──► scraper/scrape.py ──► Slack Incoming Webhook (daily post)
   (2× UTC, DST-safe)         │
                             └──► docs/data/words.json (the "database", committed back)
                                        │
                                        └──► docs/index.html on GitHub Pages (searchable history)
```

- **Scrape**: fetches the Treccani homepage, reads the word-of-day card, and (best
  effort) a short definition. Anchors on the visible label text, not CSS classes,
  and **fails loudly** on any anomaly instead of posting a blank word.
- **Store**: appends `{date, word, slug, url, definition}` to `docs/data/words.json`,
  idempotent per date. The daily commit also keeps the scheduled workflow alive.
- **History**: `docs/index.html` fetches that JSON and renders a client-side
  searchable list — this is the "what was the word on day X?" lookup.

## Zero-cost model

| Component        | Service                | Cost |
|------------------|------------------------|------|
| Daily job        | GitHub Actions (public repo) | free, unlimited |
| Storage          | JSON file in the repo  | free |
| History website  | GitHub Pages           | free |
| Slack delivery   | Incoming Webhook       | free |

## Local development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r scraper/requirements.txt pytest
cd scraper && python -m pytest        # run tests
python scrape.py --dry-run --force    # scrape + print Slack payload, no post
```

- `--force` ignores the 9am Europe/Rome guard (for off-hours testing).
- With no `SLACK_WEBHOOK_URL` set, the scraper prints the Block Kit payload instead
  of posting — the whole pipeline still runs.

## Connecting Slack (needs workspace-install permission)

You can build and validate everything **without** installing into a restricted
workspace. When you have install rights:

1. Create the app from [`slack-app-manifest.yaml`](slack-app-manifest.yaml) at
   <https://api.slack.com/apps> → *From an app manifest*.
2. Enable **Incoming Webhooks** → *Add New Webhook to Workspace* → pick a channel.
3. Add the webhook URL as a repo secret named `SLACK_WEBHOOK_URL`
   (`gh secret set SLACK_WEBHOOK_URL`).
4. `gh workflow run daily.yml` → the message appears in the channel.

**Validate before you have corporate approval:** create a free personal Slack
workspace (you're auto-admin), do steps 1–4 there. Or paste the payload from
`--dry-run` into the [Block Kit Builder](https://app.slack.com/block-kit-builder)
to preview it with no install at all.

## Legal / usage note

Treccani offers no word-of-the-day API, so the homepage is scraped. This runs
**once per day**, with an honest, identifiable User-Agent, and stores only a short
definition snippet for **personal, non-commercial** use. Treccani's `robots.txt`
permits these paths but the site discourages scraping — please keep usage minimal.
