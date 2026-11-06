"""Clean the CC0 MakeHuman textures for tulevo: plain white tee (no MakeHuman logo/url),
neutral grey shoe accents (no brand-like green), opaque-safe hair colour fill."""
import sys
import numpy as np
from PIL import Image, ImageFilter
A = sys.argv[1]  # output assets dir
S = sys.argv[2]  # MakeHuman system assets (originals)
# tee: rebuild the shirt half from the AO map, keep the jeans
d = np.asarray(Image.open(f"{S}/clothes/male_casualsuit06/male_casualsuit06_diffuse.png").convert("RGB")).astype(np.float32) / 255
ao = np.asarray(Image.open(f"{S}/clothes/male_casualsuit06/male_casualsuit06_ao.png").convert("L").filter(ImageFilter.GaussianBlur(2))).astype(np.float32) / 255
H, W = ao.shape
blue = (d[..., 2] - d[..., 0]) > 0.08
shirt = np.zeros_like(blue); shirt[: int(H * 0.44)] = True
shirt &= ~blue
rng = np.random.default_rng(3)
grain = np.asarray(Image.fromarray((rng.random((H, W)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))).astype(np.float32) / 255
tee = np.array([0.90, 0.90, 0.88]) * (0.42 + 0.58 * ao[..., None]) * (0.97 + 0.06 * grain[..., None])
out = np.where(shirt[..., None], tee, d)
out[int(H * 0.93):, int(W * 0.78):] = 0.75  # url text corner (unused UV space)
Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(f"{A}/male_casualsuit06/male_casualsuit06_diffuse.png")
# shoes: green accents -> dark grey
s = np.asarray(Image.open(f"{S}/clothes/shoes05/shoes05_diffuse.png").convert("RGBA")).astype(np.float32) / 255
g = (s[..., 1] - np.maximum(s[..., 0], s[..., 2])) > 0.06
lum = s[..., :3].mean(-1, keepdims=True)
s[..., :3] = np.where(g[..., None], lum * 0.55 + 0.05, s[..., :3])
Image.fromarray((np.clip(s, 0, 1) * 255).astype(np.uint8)).save(f"{A}/shoes05/shoes05_diffuse.png")
# hair: fill transparent texels with the hair's mean colour (looks right even if drawn opaque)
h = np.asarray(Image.open(f"{S}/hair/short02/short02_diffuse.png").convert("RGBA")).astype(np.float32) / 255
m = h[..., 3] > 0.5
h[..., :3] *= 0.42  # near-black brown
mean = h[m][:, :3].mean(0) * 0.8
h[..., :3] = np.where(m[..., None], h[..., :3], mean)
Image.fromarray((np.clip(h, 0, 1) * 255).astype(np.uint8)).save(f"{A}/short02/short02_diffuse.png")
print("ok, hair mean", mean)
