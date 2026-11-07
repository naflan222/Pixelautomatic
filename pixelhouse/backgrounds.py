"""Reviewed, independently generated camera backgrounds, never scraped store posters."""
import base64
import io
from functools import lru_cache
from pathlib import Path
from PIL import Image,ImageFilter,ImageOps,ImageStat
from .core import AutomationError

@lru_cache(maxsize=4)
def _load(path):
    image=Image.open(io.BytesIO(base64.b64decode(Path(path).read_text()))).convert('RGB')
    if min(image.size)<1024:
        raise AutomationError('Background must be at least 1024 pixels on its shortest side.')
    edges=image.convert('L').filter(ImageFilter.FIND_EDGES)
    if ImageStat.Stat(edges.crop((10,10,image.width-10,image.height-10))).mean[0]<1.2:
        raise AutomationError('Background lacks sufficient edge detail; hold for review.')
    return image

def generated_background(size,seed=0):
    files=sorted(Path('assets/backgrounds').glob('*.b64'))
    if not files:return None
    image=_load(str(files[seed%len(files)]))
    width,height=size
    if max(width/image.width,height/image.height)>1.3:
        raise AutomationError('Background would require excessive enlargement; hold for review.')
    return ImageOps.fit(image,size,method=Image.Resampling.LANCZOS,centering=(.5,.5))
