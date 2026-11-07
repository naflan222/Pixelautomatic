from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .core import AutomationError, store_image

Image.MAX_IMAGE_PIXELS = 40_000_000
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def wrap(draw, text, size, width, max_lines=4):
    while size >= 24:
        f = font(size, True)
        lines, line = [], ""
        for word in text.split():
            candidate = (line + " " + word).strip()
            if draw.textlength(candidate, font=f) > width:
                if not line:
                    break
                lines.append(line)
                line = word
            else:
                line = candidate
        else:
            if line:
                lines.append(line)
            if len(lines) <= max_lines and all(draw.textlength(x, font=f) <= width for x in lines):
                return lines, f, size
        size -= 2
    raise AutomationError("Product title is too long to render legibly; review it first.")


def render_image(post, output, product_bytes=None):
    if post.get("topic", "product") != "product":
        from .editorial_media import render_editorial
        return render_editorial(post, output, product_bytes)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    raw = product_bytes if product_bytes is not None else store_image(post["product"]["image"])
    try:
        original = Image.open(io.BytesIO(raw))
        original.load()
        original = ImageOps.exif_transpose(original).convert("RGBA")
    except Exception:
        raise AutomationError("Original product photograph could not be decoded.") from None
    if min(original.size) < 160:
        raise AutomationError("Source product photo is too small. Supply a better original before publishing.")
    logo = Image.open(io.BytesIO(base64.b64decode(Path("assets/logo.b64").read_text()))).convert("RGBA")
    theme = [(36, 92, 78), (34, 72, 104), (78, 57, 92), (89, 75, 42)][post["design_seed"] % 4]
    assets = {}
    for variant, height in (("feed", 1350), ("vertical", 1920)):
        image = Image.new("RGB", (1080, height))
        draw = ImageDraw.Draw(image)
        for y in range(height):
            ratio = math.sin(math.pi * y / height) * 0.6
            color = tuple(int(10 + v * ratio) for v in theme)
            draw.line((0, y, 1080, y), fill=color)
        # Deterministic variation is tied to the date and product, not fabricated stock/promotions.
        offset = post["design_seed"] % 140
        for radius in (330, 420, 510):
            draw.ellipse((780-radius+offset, height*.42-radius, 780+radius+offset, height*.42+radius), outline=(58, 89, 79), width=2)
        mark = ImageOps.contain(logo, (270, 90))
        image.paste(mark, (70, 55), mark)
        draw.text((72, 170), "GEAR FOR YOUR NEXT STORY", font=font(20), fill=(184, 219, 173))
        title_lines, title_font, size = wrap(draw, post["product"]["name"], 58, 930, 3)
        for index, line in enumerate(title_lines):
            draw.text((70, 210 + index * (size + 12)), line, font=title_font, fill=(247, 246, 232))
        top = 465 if height == 1350 else 620
        box_height = 500 if height == 1350 else 850
        product = ImageOps.contain(original, (900, box_height))
        x, y = (1080-product.width)//2, top + (box_height-product.height)//2
        image.paste(product, (x, y), product)
        price = post["product"]["price"]
        price_text = "Explore the collection" if price is None else (f"LKR {price:,.2f}" if price % 1 else f"LKR {price:,.0f}")
        draw.text((70, height-285), price_text, font=font(52, True), fill=(246, 246, 233))
        # Keep the moving visual hook and product name separate from price text.
        draw.rounded_rectangle((70, height-190, 680, height-115), radius=38, fill=(201, 244, 155))
        draw.text((105, height-173), "EXPLORE AT PIXELHOUSE", font=font(29, True), fill=(18, 42, 28))
        draw.text((73, height-70), "pixelhouse.lk", font=font(27), fill=(231, 239, 222))
        draw.text((73, height-345), post["headline"], font=font(27), fill=(185, 208, 185))
        destination = output / f"{variant}.jpg"
        image.save(destination, "JPEG", quality=94, optimize=True, subsampling=0)
        with Image.open(destination) as verified:
            if verified.size != (1080, height) or verified.format != "JPEG":
                raise AutomationError("Image validation failed.")
        if destination.stat().st_size > 8_000_000:
            raise AutomationError("Image exceeds Instagram's reviewed 8 MB limit.")
        assets[variant] = destination
    assets["fingerprint"] = hashlib.sha256(assets["feed"].read_bytes()).hexdigest()
    return assets


def render_video(post, output):
    output = Path(output)
    hook = output / "hook.txt"
    hook.write_text(post["hook"], encoding="utf-8")
    destination = output / "reel.mp4"
    # No music is downloaded or added. A generated silent AAC track is compatible with MP4 consumers.
    filters = ("scale=1152:2048,zoompan=z='min(zoom+0.00012,1.065)':"
               "x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=600:s=1080x1920:fps=30,"
               f"drawtext=fontfile={FONT_BOLD}:textfile='{hook.as_posix()}':"
               "fontcolor=white:fontsize=35:box=1:boxcolor=black@0.65:boxborderw=18:"
               "x=(w-tw)/2:y=150:enable='lt(t,2)'")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(output / "vertical.jpg"),
           "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", filters, "-t", "20", "-r", "30",
           "-c:v", "libx264", "-threads", "2", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", str(destination)]
    try:
        subprocess.run(cmd, check=True, timeout=300, capture_output=True)
        result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(destination)], check=True, capture_output=True, timeout=30)
        info = json.loads(result.stdout)
        stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        if stream["codec_name"] != "h264" or (stream["width"], stream["height"]) != (1080, 1920) or stream["r_frame_rate"] != "30/1" or not 19.9 <= float(info["format"]["duration"]) <= 20.1:
            raise AutomationError("Video export failed validation.")
    except (subprocess.SubprocessError, OSError, StopIteration, ValueError, KeyError):
        raise AutomationError("FFmpeg video generation/validation failed. No video was published.") from None
    return destination
