from __future__ import annotations

import time

from .core import AutomationError, utc_now


FINAL = {"published", "cancelled"}


def checkpoint(store, record, phase, **values):
    record.update(values, phase=phase, updated_at=utc_now())
    store.save()  # Must succeed before any irreversible platform call.


def instagram(post, record, meta, store, validate, *, poll_seconds=15, max_polls=24):
    if record.get("status") in FINAL:
        return
    phase = record.get("phase", "new")
    if phase == "container_request":
        checkpoint(store, record, phase, status="uncertain")
        raise AutomationError("Instagram container request was interrupted without an ID. Review before replacing it.")
    if phase == "new":
        validate()
        checkpoint(store, record, "container_request", status="pending")
        body = {"caption": post["caption"]}
        if post["kind"] == "image":
            body["image_url"] = post["media_url"]
        else:
            body.update(media_type="REELS", video_url=post["media_url"], share_to_feed=True)
        response = meta.call(f"{meta.instagram_id}/media", body)
        if not response.get("id"):
            raise AutomationError("Instagram returned no container ID.")
        checkpoint(store, record, "container_created", container_id=str(response["id"]))
    for _ in range(max_polls):
        status = meta.call(f"{record['container_id']}?fields=status_code,status")
        code = status.get("status_code")
        if code == "PUBLISHED":
            checkpoint(store, record, "done", status="published", published_at=utc_now())
            return
        if code in ("ERROR", "EXPIRED"):
            checkpoint(store, record, "container_failed", status="held")
            raise AutomationError("Instagram rejected or expired the media container.")
        if record["phase"] == "publish_request":
            # A lost publication response must never be replayed, even if the container still reads FINISHED.
            checkpoint(store, record, "publish_request", status="uncertain")
            raise AutomationError("Instagram publication outcome is uncertain; verify the account or reconcile later.")
        if record["phase"] == "done":
            return
        if code == "FINISHED":
            validate()
            checkpoint(store, record, "publish_request")
            response = meta.call(f"{meta.instagram_id}/media_publish", {"creation_id": record["container_id"]})
            if not response.get("id"):
                raise AutomationError("Instagram returned no published media ID.")
            # Commit success before fetching the optional permalink.
            checkpoint(store, record, "done", status="published", remote_id=str(response["id"]), published_at=utc_now())
            try:
                link = meta.call(f"{record['remote_id']}?fields=permalink").get("permalink")
                checkpoint(store, record, "done", url=link)
            except AutomationError:
                pass
            return
        if code != "IN_PROGRESS":
            raise AutomationError("Unexpected Instagram container status; holding without another submission.")
        time.sleep(poll_seconds)
    raise AutomationError("Instagram is still processing. Run reconcile; the saved container will be reused.")


def facebook(post, record, meta, store, validate, *, poll_seconds=15, max_polls=24):
    if record.get("status") in FINAL:
        return
    phase = record.get("phase", "new")
    if post["kind"] == "image":
        if phase != "new":
            checkpoint(store, record, phase, status="uncertain")
            raise AutomationError("Facebook photo request has an uncertain outcome. Check the Page before retrying.")
        validate()
        checkpoint(store, record, "photo_request", status="pending")
        response = meta.call(f"{meta.page_id}/photos", {"url": post["media_url"], "caption": post["caption"], "published": True})
        remote_id = response.get("post_id") or response.get("id")
        if not remote_id:
            raise AutomationError("Facebook returned no photo/post ID.")
        link = f"https://www.facebook.com/{remote_id}" if response.get("post_id") else f"https://www.facebook.com/photo/?fbid={remote_id}"
        checkpoint(store, record, "done", status="published", remote_id=str(remote_id), url=link, published_at=utc_now())
        return
    if phase == "reel_start_request":
        checkpoint(store, record, phase, status="uncertain")
        raise AutomationError("Reel initialization was interrupted without an ID. Inspect the Page before replacement.")
    if phase == "new":
        validate()
        checkpoint(store, record, "reel_start_request", status="pending")
        response = meta.call(f"{meta.page_id}/video_reels", {"upload_phase": "start"})
        if not response.get("video_id") or not response.get("upload_url"):
            raise AutomationError("Facebook returned no Reel upload session.")
        checkpoint(store, record, "reel_initialized", remote_id=str(response["video_id"]), upload_url=response["upload_url"])
    if record["phase"] == "reel_initialized":
        checkpoint(store, record, "reel_upload_request")
        meta.upload_reel(record["upload_url"], post["media_url"])
        checkpoint(store, record, "reel_uploaded")
    for _ in range(max_polls):
        response = meta.call(f"{record['remote_id']}?fields=status,permalink_url")
        status = response.get("status", {})
        published = status.get("publishing_phase", {}).get("publish_status")
        if published == "published":
            checkpoint(store, record, "done", status="published", published_at=utc_now(),
                       url=response.get("permalink_url") or f"https://www.facebook.com/reel/{record['remote_id']}")
            return
        if status.get("video_status") in ("error", "expired", "upload_failed") or any(status.get(p, {}).get("status") == "error" for p in ("processing_phase", "publishing_phase", "uploading_phase")):
            checkpoint(store, record, "reel_failed", status="held")
            raise AutomationError("Facebook rejected the Reel. Review its saved status before replacement.")
        if record["phase"] == "reel_finish_request":
            checkpoint(store, record, "reel_finish_request", status="uncertain")
            raise AutomationError("Facebook Reel finish outcome is uncertain. Reconcile again or verify manually.")
        if record["phase"] == "reel_upload_request" and status.get("uploading_phase", {}).get("status") in ("complete", "completed"):
            checkpoint(store, record, "reel_uploaded")
        ready = status.get("video_status") == "ready" or status.get("processing_phase", {}).get("status") in ("complete", "completed")
        if record["phase"] == "reel_uploaded" and ready:
            validate()
            checkpoint(store, record, "reel_finish_request")
            meta.call(f"{meta.page_id}/video_reels", {"upload_phase": "finish", "video_id": record["remote_id"], "video_state": "PUBLISHED", "description": post["caption"], "is_ai_generated": False})
            checkpoint(store, record, "reel_submitted")
        time.sleep(poll_seconds)
    raise AutomationError("Facebook is still processing. Run reconcile to reuse the saved Reel ID.")
