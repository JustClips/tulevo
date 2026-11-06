# raw/ + apps_raw/ (ForgeGUI) -> out/ + apps/ for tools/upload_icons.py --set phone / phone_apps.
#   Frame: phone body cut-out; the black screen (flood fill from the middle) is made see-through,
#          its box goes to out/meta.json as Screen = {x, y, w, h} (0-1), Aspect = w / h.
#   Wallpaper: centre crop to a tall 9:19.5 portrait.
#   apps/<Id>.png: white glyph masks (tinted in game), 256 px.
#   python3 art/phone/proc.py FRAME_RAW.png WALLPAPER_RAW.png
import glob, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__))
OUT, APPS = os.path.join(HERE, "out"), os.path.join(HERE, "apps")
os.makedirs(OUT, exist_ok=True); os.makedirs(APPS, exist_ok=True)
BEZEL = 0.03


def frame(src):
    im = Image.open(src).convert("RGBA")
    im = im.crop(im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox())
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    dark = (a[..., :3].max(axis=2) < 40) & (a[..., 3] > 200)
    lab, _ = ndimage.label(dark)
    hole = lab == lab[h // 2, w // 2]
    assert lab[h // 2, w // 2] != 0, "middle of the picture is not the black screen"
    hole = ndimage.binary_fill_holes(hole)
    # the picture's glass and bezel are both black: keep a bezel ring of BEZEL x width
    hole = ndimage.binary_erosion(hole, iterations=max(1, round(w * BEZEL)))
    ys, xs = np.where(hole)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    # keep the black glass: only clear the hole shrunk by 1 px, soft edge
    dist = ndimage.distance_transform_edt(hole)
    alpha = a[..., 3] * (1 - np.clip(dist - 1, 0, 1))
    grey = a[..., :3].mean(axis=2, keepdims=True).repeat(3, axis=2)  # titanium is grey; drops colour fringes
    out = np.dstack([grey, alpha]).astype(np.uint8)
    img = Image.fromarray(out, "RGBA")
    if img.height > 1200:
        s = 1200 / img.height
        img = img.resize((round(img.width * s), 1200), Image.LANCZOS)
    img.save(os.path.join(OUT, "Frame.png"))
    pad = 2  # the screen reaches under the black glass a little
    meta = {"Screen": [round(float(v), 5) for v in ((x0 - pad) / w, (y0 - pad) / h, (x1 - x0 + 2 * pad) / w,
                                                   (y1 - y0 + 2 * pad) / h)], "Aspect": round(w / h, 5)}
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"))
    print("frame", img.size, meta)


def wallpaper(src):
    im = Image.open(src).convert("RGB")
    h = im.height; w = round(h * 9 / 19.5)
    x = (im.width - w) // 2
    im = im.crop((x, 0, x + w, h)).resize((w * 2, h * 2), Image.LANCZOS)
    im.save(os.path.join(OUT, "Wallpaper.png"))
    print("wallpaper", im.size)


def glyphs():
    for f in sorted(glob.glob(os.path.join(HERE, "apps_raw", "*.png"))):
        im = Image.open(f).convert("RGBA")
        a = np.asarray(im).astype(np.float32)
        lum = a[..., :3].mean(axis=2) / 255
        alpha = (a[..., 3] * lum).astype(np.uint8)  # dark inner lines stay see-through
        m = Image.fromarray(alpha, "L")
        box = m.point(lambda v: 255 if v > 24 else 0).getbbox()
        g = Image.merge("RGBA", (Image.new("L", im.size, 255),) * 3 + (m,)).crop(box)
        g.thumbnail((240, 240), Image.LANCZOS)
        c = Image.new("RGBA", (256, 256), (255, 255, 255, 0))
        c.paste(g, ((256 - g.width) // 2, (256 - g.height) // 2), g)
        c.save(os.path.join(APPS, os.path.basename(f)))
        print("app", os.path.basename(f), g.size)


if len(sys.argv) > 1 and sys.argv[1] != "-":
    frame(sys.argv[1])
if len(sys.argv) > 2:
    wallpaper(sys.argv[2])
glyphs()
