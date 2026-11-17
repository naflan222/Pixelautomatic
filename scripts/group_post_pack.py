#!/usr/bin/env python3
"""Prepare Facebook Group product posts without attempting unsupported Group API publishing.

Reads Pixelhouse's live product feed and uses the existing branded image renderer.
The generated files are drafts for the owner's native Facebook Group scheduler.
No Meta credentials or GitHub write permissions are needed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageOps, ImageFilter

from pixelhouse.core import AutomationError, load_config, plan, products, store_image
from pixelhouse.media import render_image

WHATSAPP = "https://wa.me/94777466675"
TZ = ZoneInfo("Asia/Colombo")
COLUMNS = ["schedule_date", "product", "price_lkr", "image_file",
           "caption_file", "product_url", "whatsapp_url"]


def choose_products(catalog, first_day, excluded):
    """Only promote verifiably in-stock products with a known, positive price."""
    excluded = {str(item) for item in excluded}
    eligible = [
        product for product in catalog
        if product["id"] not in excluded
        and type(product.get("stock")) is int and product["stock"] > 0
        and isinstance(product.get("price"), (int, float))
        and product["price"] > 0
    ]
    # Stable rotation within this pack. Avoid duplicates and give a different
    # starting order when generating a pack for a different month.
    return sorted(
        eligible,
        key=lambda product: hashlib.sha256(
            f"group-posts:{first_day.isoformat()}:{product['id']}".encode()
        ).hexdigest(),
    )


def safe_stem(product):
    slug = re.sub(r"[^a-z0-9]+", "-", product["name"].casefold()).strip("-")
    return (slug[:42].strip("-") or "product")



def prepare_source_photo(product):
    """Use the original website photo, scaling only a local draft copy if small.

    Existing Pixelhouse Page/Instagram renderer enforces 600 px on the shortest
    edge. Small catalog originals are common; this Group-only step increases
    pixel dimensions without inventing details or editing the website image.
    """
    raw = store_image(product["image"])
    try:
        with Image.open(io.BytesIO(raw)) as source:
            source.load()
            photo = ImageOps.exif_transpose(source).convert("RGBA")
    except (OSError, ValueError):
        raise AutomationError("Source product photo is invalid.") from None
    width, height = photo.size
    if min(width, height) < 60:
        raise AutomationError("Product photo is extremely small; cannot make a useful poster.")
    factor = max(1.0, 600 / min(width, height))
    if factor > 1:
        new_size = (round(width * factor), round(height * factor))
        # Rendering memory safety for disproportionate images.
        if max(new_size) > 5500:
            raise AutomationError("Product photo has an unsuitable aspect ratio.")
        photo = photo.resize(new_size, Image.Resampling.LANCZOS)
        photo = photo.filter(ImageFilter.UnsharpMask(radius=1.2, percent=65, threshold=3))
    buf = io.BytesIO()
    photo.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), {
        "product_id": product["id"],
        "source_px": [width, height],
        "render_px": list(photo.size),
        "enlarged_for_draft": factor > 1,
        "quality_note": "Upscaling adds pixels, not original photographic detail." if factor > 1 else "",
    }

def write_pack(count, first_date, output_root):
    config = load_config()
    today = datetime.now(TZ).date()
    first_day = date.fromisoformat(first_date) if first_date else today + timedelta(days=1)
    if first_day < today:
        raise AutomationError("First scheduling date is in the past (Asia/Colombo).")

    catalog = products()
    choices = choose_products(catalog, first_day, config.get("excluded_product_ids", []))
    if not choices:
        raise AutomationError("No verified in-stock Pixelhouse products with prices; nothing exported.")

    output_root.mkdir(parents=True, exist_ok=True)
    drafts = output_root / "_render_temp"
    rows, errors, source_images = [], [], []
    for product in choices:
        if len(rows) >= count:
            break
        day = first_day + timedelta(days=len(rows))
        post = plan(product, day, "image", config.get("language", "en"))
        post.update(topic="product", ai_generated=False)
        render_dir = drafts / product["id"].replace("/", "_")
        try:
            photo_bytes, image_info = prepare_source_photo(product)
            assets = render_image(post, render_dir, product_bytes=photo_bytes)
        except (AutomationError, OSError, ValueError) as exc:
            errors.append(f"{product['name']} ({product['id']}): {exc}")
            shutil.rmtree(render_dir, ignore_errors=True)
            continue

        number = len(rows) + 1
        stem = f"{number:02d}-{safe_stem(product)}"
        image_name = f"{stem}.jpg"
        caption_name = f"{stem}.txt"
        shutil.copyfile(assets["feed"], output_root / image_name)
        caption = post["caption"].strip() + (
            f"\n\nView product: {product['url']}"
            f"\nWhatsApp enquiries: {WHATSAPP}"
        )
        (output_root / caption_name).write_text(caption + "\n", encoding="utf-8")
        source_images.append(image_info)
        rows.append({
            "schedule_date": day.isoformat(),
            "product": product["name"],
            "price_lkr": f"{product['price']:,.0f}" if product["price"] % 1 == 0
                         else f"{product['price']:,.2f}",
            "image_file": image_name,
            "caption_file": caption_name,
            "product_url": product["url"],
            "whatsapp_url": WHATSAPP,
        })
        shutil.rmtree(render_dir, ignore_errors=True)

    shutil.rmtree(drafts, ignore_errors=True)
    if not rows:
        raise AutomationError("All source product images failed validation; no drafts exported.")

    with (output_root / "SCHEDULE.csv").open("w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "generated_at": datetime.now(TZ).isoformat(),
        "first_date": first_day.isoformat(),
        "requested_posts": count,
        "prepared_posts": len(rows),
        "source": "https://pixelhouse.lk/api/products",
        "posting_method": "Facebook Group's built-in manual scheduling",
        "auto_published": False,
        "skipped_products": errors,
        "source_image_quality": source_images,
    }
    (output_root / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_root / "HOW-TO-SCHEDULE.txt").write_text(
        "PIXELHOUSE FACEBOOK GROUP PRODUCT POSTS\n\n"
        "These are DRAFTS, not published posts. Facebook no longer provides\n"
        "third-party automated publishing to Groups via the official API.\n\n"
        "On your Android Facebook app:\n"
        "1. Open the group you administer and create a post.\n"
        "2. Open the first caption .txt, copy it, and attach the matching .jpg.\n"
        "3. Tap Schedule / the calendar icon and select the date in SCHEDULE.csv.\n"
        "4. Choose your preferred local time (for example, 8:30 AM Colombo).\n"
        "5. Repeat for the remaining files; Facebook then publishes each\n"
        "   scheduled post automatically at its chosen time.\n\n"
        "Recheck price, availability and links shortly before the scheduled\n"
        "publication dates. The pack uses live data at generation time;\n"
        "future price or stock changes do not update scheduled Facebook posts.\n"
        "Only products verified in stock with a valid positive price are included.\n"
        "Existing website photos, store inventory, Facebook Page and Instagram\n"
        "automation are not changed by this workflow.\n",
        encoding="utf-8",
    )
    print(f"Prepared {len(rows)} unique group-post drafts from {len(choices)} eligible products.")
    print(f"Skipped {len(errors)} products due to image validation.")
    print(f"Made local draft-only enlarged copies of {sum(i['enlarged_for_draft'] for i in source_images)} smaller photos.")
    for reason in errors[:20]:
        print("Skipped product: " + reason)
    if len(rows) < count:
        print(f"Only {len(rows)} valid drafts were available; requested {count}.")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, choices=(7, 14, 30), default=14)
    parser.add_argument("--first-date", default="", help="YYYY-MM-DD, Asia/Colombo; default tomorrow")
    parser.add_argument("--output", default="output/facebook-group-post-pack")
    args = parser.parse_args()
    write_pack(args.count, args.first_date, Path(args.output))


if __name__ == "__main__":
    try:
        main()
    except (AutomationError, ValueError, OSError) as error:
        raise SystemExit(f"Could not prepare Facebook group pack: {error}")
