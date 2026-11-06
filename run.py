#!/usr/bin/env python3
"""One short-lived workflow invocation; no server or paid AI service required."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from pixelhouse.core import (AutomationError, GitHubStore, Meta, assert_current, due,
                             load_config, local_day, plan, products, select_product, utc_now)
from pixelhouse.media import render_image, render_video
from pixelhouse import publishing


def summary(text):
    print(text)
    path = os.getenv("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as out:
            out.write(text + "\n\n")


def render(post):
    output = Path("output") / post["slot"]
    output.mkdir(parents=True, exist_ok=True)
    assets = render_image(post, output)
    file = render_video(post, output) if post["kind"] == "video" else assets["feed"]
    manifest = {**post, "local_media": str(file), "fingerprint": assets["fingerprint"]}
    (output / "preview.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "caption.txt").write_text(post["caption"], encoding="utf-8")
    return file, assets["fingerprint"]


def meta_from_env(config):
    return Meta(config["graph_version"], os.getenv("META_PAGE_ACCESS_TOKEN"),
                os.getenv("FACEBOOK_PAGE_ID"), os.getenv("INSTAGRAM_ACCOUNT_ID"))


def validate_before_publish(post):
    if (datetime.now(timezone.utc) - datetime.fromisoformat(post["created_at"])).total_seconds() > 86400:
        raise AutomationError("Draft is over 24 hours old. Only reconcile existing publication status; do not send it now.")
    assert_current(post["product"], products())


def publish_platforms(post, config, store, meta):
    failures = []
    for platform in config["platforms"]:
        record = post["publications"].setdefault(platform, {"phase": "new", "status": "pending"})
        if record.get("status") in publishing.FINAL:
            summary(f"{platform}: {record['status']} — {record.get('url') or record.get('remote_id') or 'recorded'}")
            continue
        try:
            function = getattr(publishing, platform)
            function(post, record, meta, store, lambda: validate_before_publish(post))
            summary(f"{platform}: {record.get('status', 'pending')} — {record.get('url') or record.get('remote_id') or 'recorded'}")
        except AutomationError as exc:
            record["last_error"] = str(exc)
            record["updated_at"] = utc_now()
            # Keep the precise phase. It controls whether resumption can safely proceed.
            if record.get("phase", "new").endswith("request"):
                record["status"] = "uncertain"
            else:
                record["status"] = "held"
            store.save()
            summary(f"{platform}: needs attention — {exc}")
            failures.append(platform)
    if failures:
        raise AutomationError("Some platforms need attention: " + ", ".join(failures) + ". Inspect the saved state; do not delete it.")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["preview", "check", "initialize", "publish", "reconcile", "resolve"])
    parser.add_argument("--kind", choices=["image", "video"], default="image")
    parser.add_argument("--date", default="")
    parser.add_argument("--local", action="store_true", help="Preview locally without GitHub credentials")
    parser.add_argument("--slot", default="")
    parser.add_argument("--platform", choices=["facebook", "instagram"], default="facebook")
    parser.add_argument("--resolution", choices=["none", "verified_absent", "published", "cancel"], default="none")
    parser.add_argument("--remote-id", default="")
    args = parser.parse_args(argv)
    config = load_config()
    day = date.fromisoformat(args.date) if args.date else local_day()
    if args.local and args.command != "preview":
        raise AutomationError("--local is available only for preview.")
    store = None
    state = {"version": 1, "posts": {}}
    if not args.local:
        store = GitHubStore(os.getenv("GITHUB_REPOSITORY", ""), os.getenv("GITHUB_TOKEN", ""), config["state_branch"])
        state = store.load()
    if args.command == "initialize":
        if store.branch_exists:
            summary("State ledger already initialized. Existing history preserved.")
            return
        store.save()
        summary("Created durable posting ledger. No media generated and no posts published.")
        return
    if args.command == "check":
        meta = meta_from_env(config)
        checked = meta.check(config["platforms"])
        catalog = products()
        eligible = sum(type(p["stock"]) is int and p["stock"] > 0 for p in catalog)
        summary(f"Authorized Page: {checked['page']}. Linked accounts verified. {len(catalog)} catalog records; {eligible} in stock. No posts published.")
        return
    if args.command == "resolve":
        post = state["posts"].get(args.slot)
        if not post or args.platform not in post.get("publications", {}):
            raise AutomationError("Choose an existing slot and platform from the state ledger.")
        record = post["publications"][args.platform]
        if record.get("status") == "published":
            raise AutomationError("Published posts cannot be reset by this tool.")
        if args.resolution == "verified_absent":
            post["publications"][args.platform] = {"phase": "new", "status": "pending", "operator_verified_absent_at": utc_now()}
        elif args.resolution == "published":
            if not args.remote_id or not all(c.isdigit() or c == "_" for c in args.remote_id):
                raise AutomationError("Supply the real numeric media/post ID, not a password or token.")
            record.update(phase="done", status="published", remote_id=args.remote_id, operator_reconciled_at=utc_now())
        elif args.resolution == "cancel":
            record.update(status="cancelled", operator_cancelled_at=utc_now())
        else:
            raise AutomationError("Select a resolution. Verify the real account before using verified_absent.")
        store.save()
        summary("Recorded operator resolution. This command does not publish anything.")
        return
    if args.command == "preview":
        product = select_product(products(), state, day, args.kind, config["excluded_product_ids"])
        post = plan(product, day, args.kind, config["language"])
        file, _ = render(post)
        summary(f"Preview ready: {file}. Product facts were fetched live. Nothing uploaded publicly or published.")
        return
    if not store.branch_exists:
        raise AutomationError("Run initialize once first. A missing posting ledger must never silently reset history.")
    if not config.get("brand_approved") or not config.get("photo_rights_confirmed"):
        raise AutomationError("Review the logo and confirm photography rights in config.json before publishing.")
    if os.getenv("AUTOMATION_ENABLED", "").lower() != "true":
        raise AutomationError("Publishing is disabled. After preview and account checks, set the AUTOMATION_ENABLED repository variable to true.")
    meta = meta_from_env(config)
    meta.check(config["platforms"])
    if args.command == "reconcile":
        posts = [p for p in state["posts"].values() if p.get("media_url") and any(r.get("status") not in publishing.FINAL for r in p.get("publications", {}).values())]
        posts.sort(key=lambda p: p["slot"])
        # A bounded run protects the free runner budget. Resolve older held records before building a backlog.
        for post in posts[:3]:
            publish_platforms(post, config, store, meta)
        summary(f"Reconciliation inspected up to {min(3, len(posts))} saved slots. No new slots created.")
        return
    if day != local_day():
        raise AutomationError("New publishing is limited to today's Colombo date. Use reconcile for existing slots.")
    if not due(args.kind, day, config["start_date"]):
        summary("Not a scheduled video/photo day. No media generated or published.")
        return
    slot = f"{day}-{args.kind}"
    post = state["posts"].get(slot)
    if post is None:
        product = select_product(products(), state, day, args.kind, config["excluded_product_ids"])
        post = plan(product, day, args.kind, config["language"])
        post["publications"] = {p: {"phase": "new", "status": "pending"} for p in config["platforms"]}
        state["posts"][slot] = post
        store.save()
    if all(post.get("publications", {}).get(p, {}).get("status") in publishing.FINAL for p in config["platforms"]):
        summary("This slot is already complete. Nothing will be posted twice.")
        return
    if not post.get("media_url"):
        validate_before_publish(post)
        file, fingerprint = render(post)
        if any(p.get("fingerprint") == fingerprint for key, p in state["posts"].items() if key != slot):
            raise AutomationError("Exact repeated artwork detected; holding it for review.")
        post["media_url"] = store.upload(file)
        post["fingerprint"] = fingerprint
        store.save()
    publish_platforms(post, config, store, meta)


if __name__ == "__main__":
    try:
        main()
    except (AutomationError, ValueError, KeyError) as exc:
        summary(f"Stopped safely: {exc}")
        sys.exit(1)
