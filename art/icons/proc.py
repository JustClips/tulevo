# raw/<Name>.png (ForgeGUI) -> out/<Name>.png: pure white glyph (tinted in game with ImageColor3),
# alpha x brightness so any dark inner lines stay see-through, cropped and centred on 256 px.
import glob, os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
SIZE, MARGIN = 256, 8
for f in sorted(glob.glob(os.path.join(HERE, "raw", "*.png"))):
    im = Image.open(f).convert("RGBA")
    r, g, b, a = im.split()
    lum = Image.merge("RGB", (r, g, b)).convert("L")
    alpha = Image.eval(Image.merge("LA", (lum, a)).split()[0], lambda v: v)  # placeholder
    px_a, px_l = a.load(), lum.load()
    out_a = Image.new("L", im.size)
    oa = out_a.load()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            oa[x, y] = px_a[x, y] * px_l[x, y] // 255
    box = out_a.point(lambda v: 255 if v > 24 else 0).getbbox()
    glyph = Image.merge("RGBA", (Image.new("L", im.size, 255),) * 3 + (out_a,)).crop(box)
    glyph.thumbnail((SIZE - 2 * MARGIN, SIZE - 2 * MARGIN), Image.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    canvas.paste(glyph, ((SIZE - glyph.width) // 2, (SIZE - glyph.height) // 2), glyph)
    name = os.path.basename(f)
    canvas.save(os.path.join(HERE, "out", name))
    print(name, glyph.size)
