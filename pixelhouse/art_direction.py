"""Shared original studio artwork: layered light, grain and optical close-ups."""
import math
import random
from PIL import Image, ImageDraw, ImageFilter

PALETTES = [(12, 33, 46), (31, 26, 47), (16, 39, 35), (43, 29, 23)]


def studio_background(size, seed=0):
    width, height = size
    # Work at quarter resolution for soft physical-looking pools of light.
    w, h = width // 4, height // 4
    palette = PALETTES[seed % len(PALETTES)]
    image = Image.new('RGB', (w, h))
    pixels = image.load()
    rng = random.Random(seed)
    for y in range(h):
        for x in range(w):
            light = math.exp(-(((x-w*.72)/(w*.6))**2+((y-h*.44)/(h*.5))**2)*2)
            rim = math.exp(-(((x-w*.12)/(w*.45))**2+((y-h*.6)/(h*.4))**2)*3)
            grain = rng.uniform(-1.4, 1.4)
            pixels[x, y] = tuple(max(0, min(255, int(5 + c*(.4+light*1.9) + rim*(16 if i==0 else 7)+grain))) for i,c in enumerate(palette))
    image = image.resize(size, Image.Resampling.BICUBIC)
    beams = Image.new('RGBA', size)
    d = ImageDraw.Draw(beams)
    d.polygon([(width*.68,0),(width*.84,0),(width*.29,height),(0,height)], fill=(89,165,199,13))
    d.polygon([(width*.91,0),(width,0),(width*.72,height),(width*.58,height)],fill=(242,171,94,10))
    image = Image.alpha_composite(image.convert('RGBA'),beams.filter(ImageFilter.GaussianBlur(25)))
    return image.convert('RGB')


def lens_visual(size, seed=0, aperture=.48):
    """Original conceptual lens macro, not a photograph of a specific product."""
    w,h=size
    image=studio_background(size,seed)
    d=ImageDraw.Draw(image)
    cx,cy=w*.53,h*.52
    r=min(w*.37,h*.43)
    # Offset shadows, machined barrel rings and individual specular highlights.
    for rr in range(int(r*1.15),0,-1):
        shade=int(10+25*(1-rr/(r*1.15)))
        d.ellipse((cx-rr+12,cy-rr+20,cx+rr+12,cy+rr+20),fill=(shade,shade+4,shade+7))
    for i in range(42):
        rr=r-i*r*.009
        value=28+int(18*math.sin(i*.8)**2)
        d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),fill=(value,value+5,value+10),outline=(value+14,value+20,value+24),width=2)
    rr=r*.63
    d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),fill=(5,19,29),outline=(74,118,134),width=4)
    for i in range(24):
        radius=rr*(1-i*.022)
        d.arc((cx-radius,cy-radius,cx+radius,cy+radius),195,285,fill=(27+i*2,88+i*2,123+i*2),width=3)
        d.arc((cx-radius,cy-radius,cx+radius,cy+radius),20,83,fill=(72+i,53+i,96+i*2),width=2)
    hole=r*aperture*.75
    d.regular_polygon((cx,cy,hole),6,rotation=30,fill=(2,8,14),outline=(94,133,140),width=3)
    for angle in range(0,360,60):
        a=math.radians(angle);b=a+.65
        d.line((cx+hole*math.cos(a),cy+hole*math.sin(a),cx+rr*.93*math.cos(b),cy+rr*.93*math.sin(b)),fill=(80,111,118),width=2)
    d.arc((cx-r*.95,cy-r*.95,cx+r*.95,cy+r*.95),203,295,fill=(193,217,225),width=4)
    d.arc((cx-r*.88,cy-r*.88,cx+r*.88,cy+r*.88),25,80,fill=(225,163,91),width=3)
    return image


def motion_visual(size, blurred=False, seed=0):
    """Rendered light-trail comparison; a teaching illustration, not captured footage."""
    w,h=size
    image=studio_background(size,seed)
    d=ImageDraw.Draw(image)
    rng=random.Random(seed)
    # Layered city lights, road perspective, reflections and moving light sources.
    horizon=int(h*.47)
    for i in range(22):
        x=int(i*w/22);top=rng.randint(int(h*.12),horizon)
        d.rectangle((x,top,x+w//24,horizon+15),fill=(12,22,33))
        for yy in range(top+8,horizon,17):
            if rng.random()>.3:d.line((x+6,yy,x+w//36,yy),fill=(84,111,126),width=2)
    glow=Image.new('RGB',size);g=ImageDraw.Draw(glow)
    for i in range(9):
        x=w*.5+(i-4)*w*.055
        end=x+(i-4)*w*.12
        points=[(x,horizon),(x+(end-x)*.2,h*.65),(end,h*.95)]
        if blurred:
            g.line(points,fill=(242,174,91) if i%2 else (108,204,233),width=4)
        else:
            px,py=points[1];g.ellipse((px-5,py-5,px+5,py+5),fill=(244,196,139))
    from PIL import ImageChops
    image=ImageChops.add(image,glow.filter(ImageFilter.GaussianBlur(10)))
    image=ImageChops.add(image,glow)
    return image


def campaign_background(size, seed=0, photograph=None):
    """Use an independently generated studio scene; never enlarge store posters."""
    from .backgrounds import generated_background
    image=generated_background(size,seed)
    if image is None:
        # Crisp original optical artwork is an honest fallback if the library is absent.
        image=studio_background(size,seed)
    width,height=size
    overlay=Image.new('RGBA',size)
    d=ImageDraw.Draw(overlay)
    # Local contrast only; do not blur or wash out the generated camera detail.
    for y in range(height):
        alpha=100 if y<height*.25 else 125 if y>height*.62 else 20
        d.line((0,y,width,y),fill=(2,9,15,alpha))
    return Image.alpha_composite(image.convert('RGBA'),overlay).convert('RGB')
