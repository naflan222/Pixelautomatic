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
from .art_direction import studio_background, lens_visual, motion_visual
from .soundtrack import create_soundtrack

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
        image = studio_background((1080,height),post["design_seed"])
        draw = ImageDraw.Draw(image)
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
    # Five readable chapters instead of enlarging a single poster for 20 seconds.
    # Motion-graphics fallback, not simulated live action or a product demonstration.
    from PIL import ImageFilter
    base = Image.open(output / "vertical.jpg").convert("RGB")
    lesson = post.get("lesson")
    cards = lesson.get("cards", []) if lesson else []
    product = post.get("product") or {}
    chapters = list(cards[:3]) if cards else [
        (product.get("name", "Your next creative setup"), "Explore the details before your next shoot."),
        ("Choose with confidence", "Check your exact camera model and accessory compatibility."),
        ("Create your next story", "Discover cameras and accessories with Pixelhouse."),
    ]
    frames = [output / "vertical.jpg"]
    for index, (title, detail) in enumerate(chapters + [("Your next frame starts here.", "Explore more at pixelhouse.lk")]):
        slide = studio_background((1080,1920),post["design_seed"]+index)
        # Keep a crisp subject visual in every scene rather than blur the whole poster.
        if post.get("topic") in {"camera_tip","camera_explainer","exploded_view"}:
            from .editorial_media import diagram
            if lesson["diagram"]=="shutter" and index<2:
                visual=motion_visual((960,760),bool(index),post["design_seed"])
            elif lesson["diagram"]=="aperture" and index<2:
                visual=lens_visual((960,760),post["design_seed"],.70 if index==0 else .22)
            else:
                visual=diagram(lesson["diagram"],960,760,post["design_seed"]+index)
        else:
            # The source composition retains the actual product or landscape, without inventing footage.
            visual=base.crop((60,350,1020,1300)).resize((960,760),Image.Resampling.LANCZOS)
        slide.paste(visual,(60,370))
        from .editorial_media import logo
        logo(slide)
        draw = ImageDraw.Draw(slide)
        draw.text((80, 160), "PIXELHOUSE / " + ("EXPLORE" if index == 3 else f"0{index + 1}"), font=font(26, True), fill=(237, 172, 96))
        y = 1210
        lines, title_font, title_size = wrap(draw, title, 52, 920, max_lines=3)
        for line in lines:
            draw.text((80, y), line, font=title_font, fill="white")
            y += title_size + 17
        y += 40
        lines, detail_font, detail_size = wrap(draw, detail, 32, 920, max_lines=4)
        if y + len(lines)*(detail_size+16) > 1650:
            raise AutomationError("Video text exceeds the readable safe area; hold for review.")
        for line in lines:
            draw.text((80, y), line, font=detail_font, fill=(212, 222, 226))
            y += detail_size + 16
        draw.text((80, 1710), "pixelhouse.lk", font=font(30, True), fill="white")
        if post.get("ai_generated"):
            draw.text((80, 1770), "AI-generated travel concept", font=font(22), fill=(182, 196, 204))
        path = output / f"chapter-{index}.jpg"
        slide.save(path, "JPEG", quality=94)
        frames.append(path)
    playlist = output / "chapters.txt"
    # Generated basenames only; never interpolate user text into FFmpeg commands.
    playlist.write_text("".join(f"file '{path.name}'\nduration 4\n" for path in frames) + f"file '{frames[-1].name}'\n")
    music = create_soundtrack(output / "original-score.wav",post["design_seed"])
    post["audio_provenance"]={"source":"Pixelhouse original procedural composition","copyrighted_recordings":False,"seed":post["design_seed"]}
    filters = ("fps=30,scale=1124:2000,zoompan=z='1+0.018*sin(on/60)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps=30,fade=t=in:st=0:d=0.3,fade=t=out:st=19.6:d=0.4,"
               f"drawtext=fontfile={FONT_BOLD}:textfile='{hook.as_posix()}':expansion=none:"
               "fontcolor=white:fontsize=35:box=1:boxcolor=black@0.65:boxborderw=18:"
               "x=(w-tw)/2:y=150:enable='lt(t,2)'")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "1", "-i", str(playlist),
           "-i", str(music), "-vf", filters, "-t", "20", "-r", "30",
           "-c:v", "libx264", "-threads", "2", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", str(destination)]
    try:
        subprocess.run(cmd, check=True, timeout=300, capture_output=True)
        result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(destination)], check=True, capture_output=True, timeout=30)
        info = json.loads(result.stdout)
        stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
        if audio["codec_name"] != "aac" or int(audio["channels"]) != 2:
            raise AutomationError("Video soundtrack export failed validation.")
        if stream["codec_name"] != "h264" or (stream["width"], stream["height"]) != (1080, 1920) or stream["r_frame_rate"] != "30/1" or not 19.9 <= float(info["format"]["duration"]) <= 20.1:
            raise AutomationError("Video export failed validation.")
    except (subprocess.SubprocessError, OSError, StopIteration, ValueError, KeyError):
        raise AutomationError("FFmpeg video generation/validation failed. No video was published.") from None
    return destination
