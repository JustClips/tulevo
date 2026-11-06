"""Clean the CC0 MakeHuman textures for tulevo: plain white tee (no MakeHuman logo/url),
neutral grey shoe accents (no brand-like green), opaque-safe hair colour fill."""
import sys
import numpy as np
from PIL import Image, ImageFilter
A = sys.argv[1]  # output assets dir
S = sys.argv[2]  # MakeHuman system assets (originals)
# tee: rebuild the shirt half from the AO map, keep the jeans
d = np.asarray(Image.open(f"{S}/clothes/male_casualsuit06/male_casualsuit06_diffuse.png").convert("RGB")).astype(np.float32) / 255
# MaxFilter wipes the thin size-label text printed at the collar of the AO map.
ao = np.asarray(Image.open(f"{S}/clothes/male_casualsuit06/male_casualsuit06_ao.png").convert("L").filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(4))).astype(np.float32) / 255
H, W = ao.shape
blue = (d[..., 2] - d[..., 0]) > 0.08
shirt = np.zeros_like(blue); shirt[: int(H * 0.44)] = True
shirt &= ~blue
rng = np.random.default_rng(3)
grain = np.asarray(Image.fromarray((rng.random((H, W)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))).astype(np.float32) / 255
tee = np.array([0.90, 0.90, 0.88]) * (0.42 + 0.58 * ao[..., None]) * (0.97 + 0.06 * grain[..., None])
out = np.where(shirt[..., None], tee, d)
# jeans: the leather back-patch carries a brand name and the stitching is fine -> paint every tan/brown
# texel in the jeans half with blurred denim (no labels anywhere)
jeans = np.zeros_like(blue); jeans[int(H * 0.44):] = True
tan = jeans & ((d[..., 0] - d[..., 2]) > 0.02)
den = np.where(blue[..., None], d, 0)
cnt = np.asarray(Image.fromarray((blue * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(24))).astype(np.float32) / 255
acc = np.stack([np.asarray(Image.fromarray((den[..., c] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(24))).astype(np.float32) / 255 for c in range(3)], -1)
fill = acc / np.maximum(cnt[..., None], 1e-3)
tanm = np.asarray(Image.fromarray((tan * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))).astype(np.float32)[..., None] / 255
out = out * (1 - tanm) + fill * tanm
out[int(H * 0.93):, int(W * 0.60):] = 0.75  # url watermark corner (unused UV space)
Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(f"{A}/male_casualsuit06/male_casualsuit06_diffuse.png")
# shoes: green accents -> dark grey
s = np.asarray(Image.open(f"{S}/clothes/shoes05/shoes05_diffuse.png").convert("RGBA")).astype(np.float32) / 255
# The source sneaker is a photo scan of a branded shoe (stripes, sole logo). Keep only the low-frequency
# shape: heavy blur kills stripes/logos, then re-shade as plain white leather upper + dark rubber.
L = Image.fromarray((s[..., :3].mean(-1) * 255).astype(np.uint8))
lb = np.asarray(L.filter(ImageFilter.GaussianBlur(28))).astype(np.float32) / 255
fine = np.asarray(Image.fromarray((rng.random(lb.shape) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1))).astype(np.float32) / 255
white = lb > 0.42
upper = np.array([0.90, 0.89, 0.86]) * (0.86 + 0.14 * np.clip(lb, 0, 1))[..., None]
rubber = np.array([0.13, 0.13, 0.14]) * (0.9 + 0.2 * lb)[..., None]
col = np.where(white[..., None], upper, rubber) * (0.96 + 0.08 * fine[..., None])
col = np.asarray(Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255
s[..., :3] = col
Image.fromarray((np.clip(s, 0, 1) * 255).astype(np.uint8)).save(f"{A}/shoes05/shoes05_diffuse.png")
# hair: fill transparent texels with the hair's mean colour (looks right even if drawn opaque)
h = np.asarray(Image.open(f"{S}/hair/short02/short02_diffuse.png").convert("RGBA")).astype(np.float32) / 255
m = h[..., 3] > 0.5
h[..., :3] *= 0.42  # near-black brown
mean = h[m][:, :3].mean(0) * 0.8
h[..., :3] = np.where(m[..., None], h[..., :3], mean)
h[int(h.shape[0] * 0.93):, int(h.shape[1] * 0.60):] = [*mean, 0.0]  # url watermark corner
Image.fromarray((np.clip(h, 0, 1) * 255).astype(np.uint8)).save(f"{A}/short02/short02_diffuse.png")
# skins: the right edge has a vertical "PUBLICDOMAIN MAKEHUMAN.ORG" strip -> fill with the skin tone
for f in ("young_lightskinned_male_diffuse.png", "young_darkskinned_male_diffuse.png"):
    folder = "young_caucasian_male" if "light" in f else "young_african_male"
    k = np.asarray(Image.open(f"{S}/skins/{folder}/{f}").convert("RGB")).astype(np.float32) / 255
    kh, kw = k.shape[:2]
    tone = np.median(k[int(kh * 0.05):int(kh * 0.1), int(kw * 0.05):int(kw * 0.1)].reshape(-1, 3), axis=0)
    k[int(kh * 0.5):, int(kw * 0.955):] = tone
    Image.fromarray((np.clip(k, 0, 1) * 255).astype(np.uint8)).save(f"{A}/{f}")
# Normal maps are not shipped at all (the source ones carry a url watermark). Remove any copies.
import os
for f in ("male_casualsuit06/male_casualsuit06_normal.png", "short02/short02_normal.png", "male_casualsuit06/male_casualsuit06_ao.png"):
    if os.path.exists(f"{A}/{f}"):
        os.remove(f"{A}/{f}")
print("ok, hair mean", mean)
