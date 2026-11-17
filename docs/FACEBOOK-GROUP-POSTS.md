# Facebook Group product posts (Android)

This is a safe add-on to the existing Pixelhouse Facebook **Page** + Instagram automation.

## What this tool does

Generates branded 1080 × 1350 JPEG product cards and individual text captions from the **live** Pixelhouse website feed. Each caption includes a product URL and the Pixelhouse WhatsApp link. It exports a dated CSV schedule and a short guide.

- Choose a pack of **7**, **14**, or **30** unique product posts.
- Products must have verified positive stock and a known price at generation time. The website itself is never edited.
- Only uses the existing product photographs and existing Pixelhouse artwork renderer.
- No Facebook credentials are required for this workflow.
- No Group post is sent automatically. The official Groups publishing API was removed in April 2024.

## Use from your Android phone

1. Merge the pull request that adds this workflow, then open the **Pixelautomatic** GitHub repository.
2. Tap **Actions → Prepare Pixelhouse Facebook group posts → Run workflow**.
3. Choose **14** (or **7** / **30**) product posts and optionally enter the first date in YYYY-MM-DD format. Leave it blank to start tomorrow in Sri Lanka.
4. Open the finished run and download the pixelhouse-facebook-group-posts artifact. Extract it on Android.
5. Open SCHEDULE.csv. For each day, copy the matching caption text file, attach the matching JPEG, and use **Schedule** inside the Facebook Group you administer.
6. Review everything under your Group's **Scheduled posts** before relying on it.

Once you have scheduled them, Facebook itself automatically publishes each post at the chosen time. You do **not** need to keep your phone online.

## Important limits

The Group scheduler does not offer an official API that will accept a different product automatically every day from GitHub or your website. The native scheduler requires you to load the posts once per batch. Meta Business Suite automation can publish to a **Facebook Page**, but it does not restore the Groups API.

Prices and stock are snapshots of the live Pixelhouse website **when the pack is generated**, not live-updated in posts scheduled for later. Check them before scheduling and periodically thereafter. A future price change on Pixelhouse.lk does not edit a scheduled Facebook Group post.

Generating another pack does not remember past packs; review product names to avoid repeating ads too close together. Bad/too-small images are skipped and reported in MANIFEST.json.

See HOW-TO-SCHEDULE.txt inside the generated artifact for a short phone checklist.
