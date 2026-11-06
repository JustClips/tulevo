"""Turn a ForgeGUI render on plain white into an inventory picture (for items with no 3D model).

  python3 tools/item_icons/forge_icon.py RAW.png art/items/out/<Id>.png <px>   (160 px per cell)

Keys out the white connected to the border, soft 2 px edge, crops, centres with a 6% margin.
RifleAmmo was made this way (ForgeGUI thumbnail via the JustClips/Dev key pool, the
inventory-item-icons sheet as style reference). Then: python3 tools/upload_icons.py --set items
"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
src, out, size = sys.argv[1], sys.argv[2], int(sys.argv[3])
im = Image.open(src).convert("RGB"); a = np.asarray(im).astype(np.float32)
white = a.min(axis=2) > 228
lab, _ = ndimage.label(white)
border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
bg = np.isin(lab, list(border))
fg = ~bg
fg = ndimage.binary_opening(fg, iterations=1)
# soft edge: alpha from distance to the background, plus whiteness near the edge
dist = ndimage.distance_transform_edt(fg)
alpha = np.clip(dist / 2.0, 0, 1)
rgba = np.dstack([a, alpha * 255]).astype(np.uint8)
img = Image.fromarray(rgba, "RGBA")
img = img.crop(img.getbbox())
m = int(size * 0.06); inner = size - 2 * m
w, h = img.size; s = inner / max(w, h)
img = img.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
canvas.save(out)
