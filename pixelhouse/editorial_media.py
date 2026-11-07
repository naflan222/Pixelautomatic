"""Original educational illustrations and disclosed AI travel artwork."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps, ImageStat

from .core import AutomationError, store_image
from .content import fallback_to_tip
from .media import font, wrap

INK = (230, 237, 232)
MUTED = (157, 179, 175)
ACCENT = (255, 151, 58)
TEAL = (89, 209, 192)


def block(draw, text, xy, width, height, size=28, colour=INK, bold=False):
    x, y = xy
    for current in range(size, 19, -1):
        f = font(current, bold)
        lines, line = [], ""
        for word in text.split():
            next_line = (line + " " + word).strip()
            if draw.textlength(next_line, font=f) > width:
                if line:
                    lines.append(line)
                line = word
            else:
                line = next_line
        if line:
            lines.append(line)
        line_height = current + 10
        if len(lines) * line_height <= height and all(draw.textlength(t, font=f) <= width for t in lines):
            for index, value in enumerate(lines):
                draw.text((x, y + index * line_height), value, font=f, fill=colour)
            return
    raise AutomationError("Educational copy does not fit legibly; hold it for review.")


def canvas(height):
    image = Image.new("RGB", (1080, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / height
        draw.line((0, y, 1080, y), fill=(int(12+9*ratio), int(24+14*ratio), int(31+13*ratio)))
    return image


def logo(image):
    mark = Image.open(io.BytesIO(base64.b64decode(Path("assets/logo.b64").read_text()))).convert("RGBA")
    mark = ImageOps.contain(mark, (230, 65))
    image.paste(mark, (65, 40), mark)


def arrow(draw, start, end, colour=TEAL, width=4):
    draw.line((start, end), fill=colour, width=width)
    angle = math.atan2(end[1]-start[1], end[0]-start[0])
    p = [(end[0]-16*math.cos(angle-.5), end[1]-16*math.sin(angle-.5)), end,
         (end[0]-16*math.cos(angle+.5), end[1]-16*math.sin(angle+.5))]
    draw.line(p, fill=colour, width=width)


def diagram(kind, width, height, seed):
    image = Image.new("RGB", (width, height), (17, 36, 45))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((2, 2, width-3, height-3), radius=22, outline=(44, 76, 83), width=2)
    cx, cy = width//2, height//2
    if kind == "exploded":
        # Functional components are separated for teaching, not reverse-engineered parts.
        labels = ["LENS", "APERTURE", "SHUTTER*", "SENSOR", "PROCESSOR", "DISPLAY"]
        positions = [90 + i*(width-180)/5 for i in range(6)]
        axis_y = height*.5
        d.line((55, axis_y+25, width-45, axis_y-25), fill=(88, 122, 133), width=2)
        for i, x in enumerate(positions):
            y = axis_y + (2.5-i)*7
            colour = [(95,155,182),(128,142,152),(117,128,139),(91,143,204),(70,142,115),(97,111,131)][i]
            if i == 0:
                for offset in (28,20,12,4):
                    d.ellipse((x-42+offset/2,y-65,x+42+offset/2,y+65), fill=(29+offset,48+offset,58+offset), outline=(117,157,173), width=2)
                d.ellipse((x-34,y-52,x+34,y+52), fill=(16,49,68), outline=(107,208,224), width=4)
                d.arc((x-26,y-44,x+26,y+44), 205, 285, fill=(173,228,235), width=4)
            else:
                poly=[(x-40,y-62),(x+30,y-80),(x+45,y+60),(x-25,y+78)]
                back=[(px+9,py+8) for px,py in poly]
                d.polygon(back, fill=(9,19,26), outline=(64,90,102))
                d.polygon(poly, fill=colour, outline=(171,198,206), width=2)
                if i == 1:
                    d.ellipse((x-22,y-31,x+22,y+31), fill=(11,27,36), outline=ACCENT, width=4)
                    for a in range(6):
                        angle=a*math.pi/3
                        d.line((x+21*math.cos(angle),y+30*math.sin(angle),x+31*math.cos(angle+.8),y+44*math.sin(angle+.8)),fill=(209,217,214),width=2)
                elif i == 2:
                    for step in range(-35,45,14):
                        d.line((x-26,y+step+12,x+27,y+step-8),fill=(39,53,64),width=5)
                elif i == 3:
                    for a in range(5):
                        for b in range(7):
                            d.rectangle((x-22+a*10,y-35+b*10,x-16+a*10,y-29+b*10),fill=(137+a*12,90+b*9,191))
                elif i == 4:
                    d.rectangle((x-17,y-23,x+20,y+22),fill=(26,39,46),outline=(190,204,182),width=2)
                    for a in range(5):
                        d.line((x-28,y-18+a*9,x-18,y-18+a*9),fill=(214,193,123),width=2)
                        d.line((x+21,y-18+a*9,x+32,y-18+a*9),fill=(214,193,123),width=2)
                else:
                    d.polygon([(x-28,y-46),(x+22,y-57),(x+32,y+42),(x-17,y+55)],fill=(25,66,86),outline=(139,194,208),width=2)
            label_y = 35 if i%2==0 else height-68
            leader_y = y-88 if i%2==0 else y+90
            d.line((x,label_y+24 if i%2==0 else label_y-5,x,leader_y),fill=(113,148,155),width=2)
            text=labels[i]
            d.text((x-d.textlength(text,font=font(20,True))/2,label_y),text,font=font(20,True),fill=INK)
        d.text((25,height-28),"*Physical shutter where fitted. Simplified functional layout; designs vary.",font=font(13),fill=MUTED)
    elif kind in {"aperture", "shutter", "white_balance", "iso"}:
        if kind == "white_balance":
            names=["COOLER","NEUTRAL","WARMER"]
            colours=[(71,116,157),(105,150,139),(171,125,87)]
            for i in range(3):
                x=25+i*(width-50)/3
                w=(width-80)/3
                d.rounded_rectangle((x,50,x+w,height-45),radius=18,fill=colours[i])
                d.polygon([(x, height-75),(x+w*.42,height*.35),(x+w*.76,height*.7),(x+w,height*.47),(x+w,height-45),(x,height-45)],fill=(30+i*12,61+i*8,68))
                d.text((x+20,20),names[i],font=font(18,True),fill=INK)
        else:
            xs=[width*.28,width*.72]
            for i,x in enumerate(xs):
                radius=min(height*.28,100)
                if kind == "aperture":
                    d.ellipse((x-radius,cy-radius,x+radius,cy+radius),fill=(43,71,84),outline=TEAL,width=3)
                    hole=radius*(.64 if i==0 else .22)
                    d.ellipse((x-hole,cy-hole,x+hole,cy+hole),fill=(9,22,30),outline=ACCENT,width=4)
                    label="WIDER OPENING" if i==0 else "NARROWER OPENING"
                elif kind == "shutter":
                    if i:
                        for a in range(9):
                            xx=x-95+a*20
                            d.ellipse((xx-23,cy-23,xx+23,cy+23),fill=(55+17*a,92+8*a,98),outline=(95,135,135))
                    else:
                        d.ellipse((x-28,cy-28,x+28,cy+28),fill=ACCENT,outline=(255,218,158),width=3)
                    label="SHORT EXPOSURE" if i==0 else "LONG EXPOSURE"
                else:
                    for a in range(6):
                        for b in range(5):
                            xx=x-75+a*30; yy=cy-65+b*30
                            d.ellipse((xx,yy,xx+9,yy+9),fill=(93,198,184))
                    label="CAPTURED LIGHT" if i==0 else "GAIN + RENDERING"
                    if i:
                        d.rectangle((x-100,cy-95,x+100,cy+95),outline=ACCENT,width=5)
                d.text((x-d.textlength(label,font=font(19,True))/2,height-45),label,font=font(19,True),fill=INK)
            arrow(d,(width*.46,cy),(width*.55,cy))
    elif kind in {"composition", "framing", "field_of_view"}:
        d.rounded_rectangle((40,35,width-40,height-40),radius=15,fill=(40,78,91),outline=(97,144,147),width=2)
        d.polygon([(40,height-65),(width*.3,height*.25),(width*.48,height*.66),(width*.68,height*.38),(width-40,height*.74),(width-40,height-40),(40,height-40)],fill=(24,55,59))
        d.ellipse((width*.73,65,width*.73+45,110),fill=(243,203,129))
        if kind == "composition":
            for ratio in (1/3,2/3):
                d.line((40+(width-80)*ratio,35,40+(width-80)*ratio,height-40),fill=INK,width=2)
                d.line((40,35+(height-75)*ratio,width-40,35+(height-75)*ratio),fill=INK,width=2)
        else:
            for scale,col in [(1,INK),(.68,TEAL),(.38,ACCENT)]:
                w=(width-80)*scale;h=(height-75)*scale
                d.rectangle((cx-w/2,cy-h/2,cx+w/2,cy+h/2),outline=col,width=4)
            d.text((60,50),"WIDE / MEDIUM / CLOSE" if kind=="framing" else "WIDER / NARROWER VIEW",font=font(18,True),fill=INK)
    elif kind == "triangle":
        points=[(cx,60),(width*.2,height-70),(width*.8,height-70)]
        d.polygon(points,outline=TEAL,width=5)
        for p,label in zip(points,["APERTURE","SHUTTER","ISO"]):
            d.ellipse((p[0]-27,p[1]-27,p[0]+27,p[1]+27),fill=(30,60,72),outline=ACCENT,width=3)
            yy=p[1]-52 if label=="APERTURE" else p[1]+36
            d.text((p[0]-d.textlength(label,font=font(22,True))/2,yy),label,font=font(22,True),fill=INK)
        d.text((cx-82,cy+20),"EXPOSURE",font=font(25,True),fill=INK)
    elif kind == "histogram":
        d.line((70,height-70,width-60,height-70),fill=INK,width=3)
        for i in range(45):
            x=80+i*(width-160)/45
            h=35+130*math.exp(-((i-25)/12)**2)+40*math.sin(i/6)**2
            d.rectangle((x,height-70-h,x+11,height-70),fill=TEAL)
        d.line((width-100,45,width-100,height-70),fill=ACCENT,width=4)
        d.text((65,height-45),"DARK TONES",font=font(18,True),fill=INK)
        d.text((width-220,height-45),"HIGHLIGHTS",font=font(18,True),fill=INK)
    else:
        for i,(title,sub) in enumerate([("LENS","LIGHT"),("SENSOR","SIGNAL"),("PROCESSOR","IMAGE")]):
            x=35+i*(width-40)/3
            w=(width-110)/3
            d.rounded_rectangle((x,height*.24,x+w,height*.75),radius=18,fill=(31,65,80),outline=TEAL,width=3)
            d.text((x+18,height*.36),title,font=font(24,True),fill=INK)
            d.text((x+18,height*.55),sub,font=font(20),fill=ACCENT)
            if i<2:arrow(d,(x+w+4,cy),(x+w+31,cy))
    return image


def _scene(post, output):
    settings=post.get("ai_image",{})
    if settings.get("provider") != "local_cpu":
        raise AutomationError("Local AI landscape generation is disabled.")
    request_file=output/"scene-request.json"
    scene=output/"generated-scene.png"
    request_file.write_text(json.dumps(post),encoding="utf-8")
    env=os.environ.copy()
    for name in ("META_PAGE_ACCESS_TOKEN", "FACEBOOK_PAGE_ID", "INSTAGRAM_ACCOUNT_ID", "GITHUB_TOKEN"):
        env.pop(name, None)
    env.setdefault("HF_HUB_DISABLE_XET","1")
    env.setdefault("HF_HUB_DISABLE_PROGRESS_BARS","1")
    try:
        subprocess.run([sys.executable,"-m","pixelhouse.ai_images","--post",str(request_file),"--output",str(scene)],env=env,check=True,timeout=min(900,max(60,int(settings.get("timeout_seconds",600)))),capture_output=True)
    except (subprocess.SubprocessError,OSError):
        raise AutomationError("CPU AI generation was unavailable or exceeded its time limit.") from None
    image=Image.open(scene).convert("RGB")
    if min(image.size)<512 or max(ImageStat.Stat(image).stddev)<4:
        raise AutomationError("Generated landscape failed the image quality check.")
    from .ai_images import MODEL,REVISION
    post["ai_provenance"]={"model":MODEL,"revision":REVISION,"seed":post["design_seed"],"steps":20,"source":"local CPU inference"}
    return image


def render_editorial(post, output, product_bytes=None, scene_image=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    scene=None;photo=None
    if post["topic"]=="travel":
        try:scene=scene_image if scene_image is not None else _scene(post,output)
        except AutomationError as exc:
            fallback_to_tip(post,str(exc))
    if post["topic"]=="accessory_explainer":
        raw=product_bytes if product_bytes is not None else store_image(post["product"]["image"])
        try:
            photo=ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGBA")
            photo.load()
            if min(photo.size) < 160:
                raise AutomationError("Accessory photograph is too small for publishing.")
        except Exception:raise AutomationError("Accessory photograph could not be decoded.") from None
    result={}
    for variant,height in (("feed",1350),("vertical",1920)):
        if scene is not None:
            image=ImageOps.fit(scene,(1080,height),method=Image.Resampling.LANCZOS)
            shade=Image.new("RGBA",image.size)
            sd=ImageDraw.Draw(shade)
            sd.rectangle((0,0,1080,130),fill=(0,0,0,80))
            for y in range(height-530,height):
                opacity=int(225*(y-(height-530))/530)
                sd.line((0,y,1080,y),fill=(3,14,20,opacity))
            image=Image.alpha_composite(image.convert("RGBA"),shade).convert("RGB")
            logo(image);d=ImageDraw.Draw(image)
            block(d,post["destination"]["name"] + ", reimagined.",(65,height-400),940,160,54,bold=True)
            d.text((67,height-245),"Inspired by "+post["destination"]["name"],font=font(30),fill=INK)
            block(d,"AI-generated travel concept. Not a location photograph.",(67,height-175),945,80,23,colour=INK)
            d.text((67,height-75),"pixelhouse.lk",font=font(30,True),fill=INK)
        else:
            image=canvas(height);logo(image);d=ImageDraw.Draw(image)
            category={"camera_tip":"CREATOR ACADEMY / CAMERA TIP","camera_explainer":"CAMERA EXPLAINED","exploded_view":"CONCEPTUAL CAMERA ANATOMY","accessory_explainer":"ACCESSORY EXPLAINED"}[post["topic"]]
            d.text((65,130),category,font=font(19,True),fill=ACCENT)
            block(d,post["lesson"]["title"],(60,175),960,145,52,bold=True)
            top=350
            graphic_h=480 if height==1350 else 900
            if photo is not None:
                panel=Image.new("RGBA",(960,graphic_h),(245,246,242,255))
                product=ImageOps.contain(photo,(900,graphic_h-25))
                panel.alpha_composite(product,((960-product.width)//2,(graphic_h-product.height)//2))
                image.paste(panel.convert("RGB"),(60,top))
            else:
                image.paste(diagram(post["lesson"]["diagram"],960,graphic_h,post["design_seed"]),(60,top))
            summary_top=top+graphic_h+30
            summary_h=20 if height==1350 else 50
            # The full explanation belongs in the caption; artwork prioritises the visual.
            card_top=summary_top+summary_h+20
            card_h=210 if height==1350 else 265
            for i,(heading,text) in enumerate(post["lesson"]["cards"]):
                x=60+i*325
                d.rounded_rectangle((x,card_top,x+310,card_top+card_h),radius=15,fill=(23,46,55),outline=(51,82,87),width=2)
                block(d,heading,(x+17,card_top+19),275,70,25,colour=ACCENT,bold=True)
                block(d,text,(x+17,card_top+88),275,card_h-100,23,colour=INK)
            note="Conceptual illustration; not model-specific, not to scale, not a repair guide." if post["topic"]=="exploded_view" else "Educational illustration. Camera designs and real-world results vary." if photo is None else "Original product photograph. Verify exact camera and mounting compatibility."
            block(d,note,(65,height-153),950,68,20,colour=MUTED)
            d.text((65,height-65),"pixelhouse.lk",font=font(27,True),fill=INK)
            stamp = "ACADEMY / " + date.fromisoformat(post["date"]).strftime("%d %b %Y").upper()
            d.text((690,height-61),stamp,font=font(16),fill=MUTED)
        destination=output/f"{variant}.jpg"
        image.save(destination,"JPEG",quality=94,optimize=True,subsampling=0)
        with Image.open(destination) as check:
            if check.size!=(1080,height) or check.format!="JPEG":raise AutomationError("Editorial media dimensions or format are invalid.")
        if destination.stat().st_size>8_000_000:raise AutomationError("Editorial image exceeds the reviewed platform size limit.")
        result[variant]=destination
    result["fingerprint"]=hashlib.sha256(result["feed"].read_bytes()).hexdigest()
    return result
