# 📖 Parola del giorno → Slack

> Every morning, the Italian **word of the day** from [Treccani](https://www.treccani.it/)
> lands in a Slack channel — and every word is kept in a searchable public archive.

A tiny, fully **serverless and zero-cost** project: no server to run, no database to
pay for, no paid tier anywhere. It runs entirely on GitHub Actions and GitHub Pages.

**Live archive:** https://cravingpixels.github.io/treccani-parola-del-giorno/

---

## What it does

- 🕘 **Posts the word to Slack** each morning (default ~9:00 Italy time, configurable) with its Treccani link and a short definition.
- 💬 **`/parola` on demand** — type `/parola` for today, `/parola ieri` for yesterday, or `/parola 2026-07-15` (also `15/07/2026`) for any past day.
- 🗄️ **Archives every word** so you can look up *"what was the word on 15 July?"* at any time.
- 🔎 **Browsable history** — a small static page with instant client-side search by word or date.

## How it works

```
      GitHub Actions (polls every 30 min, morning)
                 │
                 ▼
        scraper/scrape.py
        ├─ capture:  is the homepage word NEW? ──► append to docs/data/words.json ──┐
        └─ notify:   at/after POST_HOUR, once/day ──► Slack Incoming Webhook         │
                                                                                     ▼
   /parola in Slack ──► Cloudflare Worker (worker/) ──reads──► GitHub Pages (docs/) ─┤
                                                                                     │
        GitHub Pages (docs/index.html) ..... searchable history site ◄───────────────┘
```

The **daily post** is push-based (GitHub Actions → webhook). The **`/parola` command**
is pull-based: a tiny Cloudflare Worker verifies the Slack request signature, reads the
public `words.json`, and replies — both read from the same archive, so they never drift.

Treccani flips the word at an unknown (non-midnight) time, so instead of guessing,
the workflow **polls through the morning** and the scraper does two independent things:

1. **Capture** — reads the homepage word and stores it *only if it's new* (different
   from the last archived word). This keeps `docs/data/words.json` up to date as soon
   as Treccani rolls over, and naturally skips days where the word doesn't change.
2. **Notify** — posts the day's word to Slack **once**, at or after `POST_HOUR`
   (Europe/Rome). Because storage is idempotent per day and posting is tracked with a
   `last_posted_date`, the many polling runs de-duplicate themselves: you get exactly
   one message, and a late Treccani update is still caught.

The updated archive is committed back to the repo; GitHub Pages serves it — no backend.

## Why it costs nothing

| Piece            | Runs on                        | Cost |
|------------------|--------------------------------|------|
| Daily job        | GitHub Actions (public repo)   | free, unlimited minutes |
| Archive storage  | a JSON file in the repo        | free |
| History website  | GitHub Pages                   | free |
| Slack delivery    | Incoming Webhook               | free |
| `/parola` command | Cloudflare Worker              | free (100k req/day, no card) |

A nice side effect: the daily commit also keeps the scheduled workflow from being
auto-disabled for inactivity. Cron runs in UTC, so the schedule (`*/30 3-11 * * *`)
brackets the Italian morning across daylight-saving changes, and `scrape.py` decides
the real 9 AM (Europe/Rome) moment to post.

## Configuration

| Name | Where | Sensitive? | Purpose |
|------|-------|-----------|---------|
| `SLACK_WEBHOOK_URL` | repo **Secret** | **Yes** — treat as a password | Target channel for the daily post. Never committed; encrypted; not in logs. The channel identity is encoded inside this URL, so nothing else about your channel lives in the repo. |
| `POST_HOUR` | repo **Variable** | No | Hour (Europe/Rome, 0–23) to post at. Defaults to `9` if unset. Set it in repo Settings, not in code. |
| `SLACK_SIGNING_SECRET` | Cloudflare Worker **secret** | **Yes** | Lets the Worker verify that `/parola` requests really come from Slack. Set with `wrangler secret put`, never committed. |
| `WORDS_URL` | Worker var (`wrangler.toml`) | No | Public archive URL the Worker reads. |

Nothing that identifies your Slack workspace or channel is stored in the repository —
the public repo contains only the (public) Treccani words.

## Reliability

The scraper is deliberately defensive. It anchors on Treccani's visible
**"Parola del giorno"** element rather than fragile CSS class names, sanity-checks
the extracted word, and **fails loudly** — posting a distinct alert to Slack instead
of ever publishing a blank or wrong word. The definition snippet is best-effort: if
it can't be extracted, the word and link are still posted. Because the archive is the
only record of past words (Treccani exposes no historical feed), the polling schedule
is designed so a delayed or missed run doesn't drop a day — the next run captures it.

## Setup — adding the app to your Slack workspace

> **Need admin?** Installing an app into a company workspace usually needs a Workspace
> Owner / admin to approve it. You can build and test *everything* first in a **free
> personal Slack workspace** (create one at <https://slack.com/create> — you're the admin
> there), then repeat step 3 in the company workspace once approved.

### 1. Enable GitHub Pages (the archive the app reads)

Repo **Settings → Pages → Source: `main` / `/docs`**. Confirm
`https://cravingpixels.github.io/treccani-parola-del-giorno/data/words.json` loads.

### 2. Deploy the `/parola` command (Cloudflare Worker)

Free, no credit card. From the `worker/` folder:

```bash
cd worker
npx wrangler login          # opens the browser once
npx wrangler deploy         # prints your Worker URL, e.g. https://treccani-parola-del-giorno.<you>.workers.dev/
```

Copy that Worker URL — you'll paste it into the manifest in the next step. (You'll set
its `SLACK_SIGNING_SECRET` in step 4, once the app exists.)

### 3. Create the Slack app and install it

1. In [`slack-app-manifest.yaml`](slack-app-manifest.yaml), replace the placeholder
   `slash_commands.url` with your Worker URL from step 2.
2. Go to <https://api.slack.com/apps> → **Create New App** → **From an app manifest** →
   pick your workspace → paste the manifest → **Create**.
3. Left sidebar → **Incoming Webhooks** → toggle **On** → **Add New Webhook to Workspace**
   → choose the channel → **Allow**.
   *(In a restricted company workspace, this is where an admin-approval request is sent —
   the app isn't live until they approve.)*
4. Copy the generated **Webhook URL** and store it in the repo:
   ```bash
   gh secret set SLACK_WEBHOOK_URL     # paste the webhook URL when prompted
   ```

### 4. Give the Worker the signing secret

In the Slack app → **Basic Information → App Credentials → Signing Secret** → copy it, then:

```bash
cd worker
npx wrangler secret put SLACK_SIGNING_SECRET   # paste the signing secret
```

### 5. (Optional) Choose the post time

Defaults to 9 AM Europe/Rome. To change it:

```bash
gh variable set POST_HOUR --body 8    # e.g. post at 08:00 Italy time
```

### Done

- **Daily post** — the schedule is already active; to fire one now:
  ```bash
  gh workflow run daily.yml -f force=true
  ```
- **On demand** — in Slack: `/parola`, `/parola ieri`, `/parola 2026-07-15`.

## Local development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r scraper/requirements.txt pytest

cd scraper && python -m pytest        # run the tests
python scrape.py --dry-run            # scrape and print the Slack payload; no writes, no post
```

- `--dry-run` previews the [Block Kit](https://app.slack.com/block-kit-builder) payload
  for the current word without touching the archive or posting (works with no webhook set).
- `--force` posts immediately, ignoring the `POST_HOUR` gate (it still won't post if
  there's no fresh word for today). `POST_HOUR=8 python scrape.py` overrides the hour locally.

## Project layout

```
.github/workflows/daily.yml   # the scheduled scrape → post → commit job
.github/workflows/test.yml    # runs Python + Worker tests on every push / PR
scraper/scrape.py             # fetch, parse, store, post
scraper/tests/                # parser + storage tests (with a saved homepage fixture)
worker/src/                   # Cloudflare Worker for the /parola slash command
worker/test/                  # Worker tests (signature verification, date parsing, lookup)
worker/wrangler.toml          # Worker deploy config
docs/index.html               # the searchable history site (GitHub Pages)
docs/data/words.json          # the archive
slack-app-manifest.yaml       # one-click Slack app definition (webhook + slash command)
```

## A note on scraping & copyright

Treccani doesn't offer a word-of-the-day API, so this reads the public homepage
**once per day** with an honest, identifiable User-Agent and stores only a short
definition snippet. It's intended for **personal, non-commercial** use. Please keep
usage minimal and respect Treccani's terms — the daily word and its definitions are
their copyrighted content.
