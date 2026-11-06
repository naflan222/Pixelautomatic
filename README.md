# Pixelhouse automatic Facebook + Instagram posting

**No paid server. No database subscription. No paid AI API. No MacroDroid required.**

This repository runs short GitHub Actions jobs to import real Pixelhouse products, create branded product advertisements, and publish through official Meta APIs. Your phone can be switched off.

**Status: publishing is disabled until you complete setup. No account has been connected by installing this code.**

## What it does

| Task | Schedule / behavior |
|---|---|
| Product photograph advertisement | Every day around **08:30 Asia/Colombo** |
| 20-second branded motion video / Reels | Every **three calendar days** around **18:30 Asia/Colombo**, beginning on `start_date` |
| Product facts | Fresh `https://pixelhouse.lk/api/products`; only verified positive stock |
| Prices | Uses actual numeric LKR price; omits unknown prices; no invented discounts or bestseller claims |
| Product rotation | Avoids the last seven products where stock allows; oldest-use preference |
| Images | JPEG, 1080×1350 feed and 1080×1920 preview |
| Videos | MP4, H.264, 1080×1920, 30fps, 20s, branded; generated silent AAC track, no copyrighted music |
| Platforms | Facebook Page photos + Reels, linked Instagram professional feed + Reels |
| History | Durable JSON checkpoints in the `automation-state` branch |
| Media | Opaque content-addressed public raw GitHub files on that branch, verified before Meta submission |
| Languages | English, Sinhala, mixed Sinhala-English caption templates |

These are genuine-photo compositions and motion graphics, **not generative-AI cinematic scenes**. They preserve the supplied product photograph. The storefront's custom API has been checked; WooCommerce is not assumed. Zero/unknown stock is excluded. Original photographs with embedded artwork retain that artwork; the system does not invent missing product imagery or capabilities.

These files are ready for the repository root. If copying the standalone package into another empty repository, see [Android installation](docs/INSTALL-FROM-ANDROID.md).

## Set up from Android

Use Chrome's **Desktop site** option if GitHub or Meta hides a setting.

### 1. Make sure GitHub Actions is available

Open this repository → **Actions**. Enable workflows if GitHub asks. Open Settings → Actions → General and allow the included official GitHub Actions. The publishing workflow requests `contents: write` for its dedicated history/media branch; repository policies must permit it.

Do not add a credit card or buy a server for this setup. Public repositories on standard hosted runners can use GitHub's free allowance under its current policies. Check your account's Billing / Actions limits. No paid runners are configured here.

### 2. Generate a free preview first

A successful **Tests** run on `main` also creates a `pixelhouse-initial-previews` artifact with an image and video, without using any social credentials. You can inspect that first, or generate a fresh preview below.

Actions → **Pixelhouse Facebook + Instagram** → **Run workflow**:

- Branch: `main`
- Command: `preview`
- Kind: `image`

When it finishes, open the run → Artifacts → download `pixelhouse-preview-...`. Extract the ZIP on Android and inspect `feed.jpg`, `vertical.jpg`, `caption.txt`, and `preview.json`.

Repeat with `kind: video` and inspect `reel.mp4`. Preview needs no Meta credentials and does not publish anything or create public marketing files. Artifacts are retained for three days.

### 3. Review and edit `config.json`

Open `config.json` → pencil/Edit → set:

```json
"start_date": "YYYY-MM-DD",
"language": "en",
"brand_approved": true,
"photo_rights_confirmed": true
```

Use your real start date in Colombo. The first video is scheduled on that date, then start+3, start+6, etc. Only confirm the two flags after reviewing the Pixelhouse logo and confirming rights to the store's photographs. Keep `platforms` as `["facebook", "instagram"]`, or temporarily select `["facebook"]` for the first account test. You can exclude products by string ID in `excluded_product_ids`.

### 4. Connect your business through Meta

Follow **[META-SETUP.md](docs/META-SETUP.md)**. You need:

- Control of the Facebook Page.
- A professional Instagram account linked to that Page.
- A Meta developer app with the applicable publishing permissions.
- An authorized **Page** access token (not your Facebook password).

App permissions/review, business verification and token renewal are Meta requirements; this project does not bypass them. No account passwords are collected.

### 5. Add three GitHub Secrets

Repository → Settings → Secrets and variables → Actions → **Secrets** → New repository secret:

| Secret name | Value |
|---|---|
| `META_PAGE_ACCESS_TOKEN` | Authorized long-lived Facebook Page token |
| `FACEBOOK_PAGE_ID` | Numeric Facebook Page ID |
| `INSTAGRAM_ACCOUNT_ID` | Numeric linked Instagram professional account ID |

**Never paste these into a code file, Issue, workflow log, or chat.** GitHub automatically supplies `GITHUB_TOKEN`; you do not create that secret.

### 6. Initialize the posting history once

Actions → Pixelhouse Facebook + Instagram → Run workflow → command **`initialize`**.

This creates `automation-state` and `automation/state.json`. It does not publish. Subsequent runs preserve history. **Do not delete/reset this branch or ledger**: it prevents duplicate posts. If it is lost, restore it before enabling new publishing.

### 7. Check the accounts without posting

Run the same workflow with command **`check`**.

It verifies that the token belongs to your configured Facebook Page, that the configured Instagram account is linked, and that live products are available. It does not prove all publishing permissions are approved; that requires a real test post.

### 8. Enable automation and publish your first real test

Settings → Secrets and variables → Actions → **Variables** → New repository variable:

```text
Name: AUTOMATION_ENABLED
Value: true
```

This enables scheduled jobs **and** manual publishing. Add it only after previews, rights confirmation, account checks and the schedule are ready. Then run workflow with command **`publish`**, kind **`image`**. This posts today's slot to the platforms selected in `config.json`. Verify the actual Facebook and Instagram posts and recorded links.

A repeated publish run for the same date/kind skips completed platform posts. Video publishing occurs only on a configured video day; you can always preview video on any day. To test a real video today, set `start_date` to today's Colombo date before running publish/video.

### 9. Leave it running

The image job runs at 03:00 UTC (08:30 Colombo). The video check runs at 13:00 UTC (18:30 Colombo) every day, but generates/publishes only on the three-day cadence. GitHub schedules are approximate and can be delayed or dropped; missed days are not automatically backfilled. Your Android phone does not need to stay on.

For failure alerts, configure GitHub's Actions notification/email preferences. GitHub's Android application can make failures easier to monitor; it is not required for posting. This free edition does not send WhatsApp or Telegram notifications.

## Pause and recover

- **Pause:** change repository variable `AUTOMATION_ENABLED` to `false`, or disable this workflow under Actions. An already-running publishing request may still finish. Pausing stops future jobs; it does not retract posts.
- **Resume:** set the variable back to `true` after checking credentials and stock.
- **Processing / lost response:** run command `reconcile`. It reuses recorded Instagram containers/Facebook Reel IDs and never starts new daily slots. It can finish a previously prepared post only while its facts remain current and its draft is under 24 hours old.
- **Uncertain photo/publish outcome:** inspect the real Page/profile first. Run `resolve` with the affected slot, platform, and `published` plus the real post ID, or `cancel`. Use `verified_absent` only after confirming that no post was published; it permits a later retry. Resolve itself does not post anything. Never delete state as a retry technique.
- **Changed price/stock:** the workflow stops before publication. Review it; keep the stale slot held/cancelled rather than overriding factual checks. The next day selects from current inventory.
- **Expired/revoked token:** reconnect through Meta and update the GitHub secret. Page access can be invalidated by permissions/password/business changes even when the token debugger lists no fixed expiry.
- **Public raw media blocked by Meta:** preserve the saved records, cancel the affected slot if necessary, and use a compatible public media host before retrying. This transport is verified for cookie-free delivery; Meta acceptance must still be tested with your app.

No automatic retry replays a possibly successful photo/final-publication request. This can require occasional account inspection; avoiding duplicates takes priority over pretending every error can self-repair.

## Costs and practical limits

- No paid image/video AI, database, hosting subscription, or advertising spend is configured. This does not buy Facebook/Instagram ads; it publishes organic posts.
- GitHub's current free-runner, storage, fair-use and inactivity policies apply. Public scheduled workflows can be disabled after extended repository inactivity; watch GitHub's notifications and re-enable as needed. This is not a paid 24/7 uptime guarantee.
- Generated marketing files and posting records are **public** on the state branch. Tokens are not written there. Do not use private images/customer data. The sample video is about 1–2 MB; git history accumulates media over time. Monitor repository size and migrate media/history storage if necessary; deleting files does not remove their old git blobs.
- No trend feed, paid AI creativity, sales analytics, guaranteed follower growth, dashboard server, multi-user approval UI, TikTok, or WhatsApp is included in this focused free edition.
- Template captions avoid unverified features, prices, offers and testimonials. Review your initial samples for spelling, source-image quality and brand suitability before enabling automation.
- Actions are pinned to upstream commit IDs. Dependencies are pinned. Updates should be reviewed and tested before changing them.

## Local development and testing

Requires Python 3.12, Pillow, FFmpeg/libx264 and DejaVu fonts:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run.py preview --local --kind image
python run.py preview --local --kind video
```

Local preview makes live read-only requests to Pixelhouse but needs no social token or GitHub token. Unit tests use synthetic fixtures and mocked platform responses; no live posts are made. Never use actual tokens in test fixtures. Live social publishing has to be tested after your authorization.
