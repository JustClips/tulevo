"""Generates seamless, tileable PBR texture sets for the hypercar's materials (numpy only).

  blender --background --python make_tiles.py      (or plain python with numpy + Pillow)

Writes OUT/tiles/<Name>_{Color,Normal,Roughness,Metalness}.png at 1024 px (Roblox's max texture
size). Everything is built from periodic functions or FFT noise, so the edges wrap seamlessly.
  Carbon       2x2 twill carbon-fibre weave under clear coat
  Leather      fine pebbled leather grain
  Perforated   leather with staggered perforation holes (steering-wheel grips, seat centres)
  Alcantara    soft suede microfibre
  BrushedAlu   brushed aluminium
  Honeycomb    black hexagon grille mesh
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import common
    OUT = os.path.join(common.OUT, "tiles")
except Exception:
    OUT = os.path.join(r"C:\out\car918\work", "tiles")
os.makedirs(OUT, exist_ok=True)

N = 1024
rng = np.random.default_rng(918)
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N   # 0..1, periodic over the tile


def fft_noise(beta=2.0, lo=2, hi=None, seed=None):
    """Periodic noise with a 1/f^beta spectrum between frequencies lo..hi (cycles per tile)."""
    r = np.random.default_rng(seed) if seed is not None else rng
    f = np.fft.fftfreq(N)[:, None] ** 2 + np.fft.fftfreq(N)[None, :] ** 2
    f = np.sqrt(f) * N
    amp = np.where(f > 0, 1.0 / np.maximum(f, 1e-6) ** (beta / 2), 0)
    amp[f < lo] = 0
    if hi:
        amp[f > hi] = 0
    ph = np.exp(2j * np.pi * r.random((N, N)))
    n = np.real(np.fft.ifft2(amp * ph))
    n -= n.mean()
    return n / (np.abs(n).max() + 1e-9)


def aniso_noise(axis=1, length=60, seed=None):
    """Streaky noise: white noise blurred along one axis (periodic), for fibres / brushing."""
    r = np.random.default_rng(seed) if seed is not None else rng
    n = r.standard_normal((N, N)).astype(np.float32)
    k = np.zeros(N, np.float32)
    k[:length] = 1.0 / length
    K = np.fft.fft(k)
    n = np.real(np.fft.ifft(np.fft.fft(n, axis=axis) * (K[None, :] if axis == 1 else K[:, None]), axis=axis))
    n -= n.mean()
    return n / (np.abs(n).max() + 1e-9)


def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    n = np.stack([-dx, dy, np.ones_like(h)], -1)  # OpenGL / glTF convention (+Y up)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def write_png(path, a):
    """Save an (N, N) or (N, N, 3) array of 0..1 values as an 8-bit PNG, rows top to bottom."""
    a = np.clip(np.asarray(a, np.float32), 0, 1)
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, -1)
    try:
        from PIL import Image
        Image.fromarray((a * 255 + 0.5).astype(np.uint8), "RGB").save(path)
        return
    except ImportError:
        pass
    import bpy  # running inside Blender: write through an image datablock (origin bottom-left)
    im = bpy.data.images.new(os.path.basename(path), N, N, alpha=False)
    im.colorspace_settings.name = 'Non-Color'  # store the values exactly as given
    rgba = np.concatenate([np.flipud(a), np.ones((N, N, 1), np.float32)], -1)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)


def save(name, color, height, strength, rough, metal):
    write_png(os.path.join(OUT, f"{name}_Color.png"), color)
    write_png(os.path.join(OUT, f"{name}_Normal.png"), normal_from_height(height, strength))
    write_png(os.path.join(OUT, f"{name}_Roughness.png"), np.broadcast_to(rough, (N, N)))
    write_png(os.path.join(OUT, f"{name}_Metalness.png"), np.broadcast_to(metal, (N, N)))
    print("tile", name)


def srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


# ---------------------------------------------------------------- carbon fibre (2x2 twill)
T = 16                                   # tows across the tile
u, v = xx * T, yy * T
i, j = np.floor(u).astype(int), np.floor(v).astype(int)
fu, fv = u - i, v - j
warp_on_top = ((i - j) % 4) < 2          # the twill's diagonal stepping
# each tow is a rounded bundle: height across the tow, small dip at the crossings
across = np.where(warp_on_top, fv, fu)
along = np.where(warp_on_top, fu, fv)
h = np.cos((across - 0.5) * np.pi) * 0.8 + np.cos((along - 0.5) * np.pi) * 0.2
fib_x = aniso_noise(1, 90, seed=1)
fib_y = aniso_noise(0, 90, seed=2)
fib = np.where(warp_on_top, fib_x, fib_y)
h += fib * 0.15
# the two tow directions catch light differently (the classic carbon checker sheen)
sheen = np.where(warp_on_top, 0.075, 0.035) * (0.75 + 0.5 * np.cos((across - 0.5) * np.pi))
lin = 0.004 + sheen * 0.55 + fib * 0.004
col = np.stack([lin * 0.95, lin * 0.97, lin * 1.05], -1)
save("Carbon", srgb(col), h, 6.0, 0.22 + 0.06 * (1 - h / h.max()), 0.0)

# ---------------------------------------------------------------- leather grain
grain = fft_noise(1.2, lo=40, hi=260, seed=3)
cells = np.abs(fft_noise(0.6, lo=90, hi=180, seed=4))
h = grain * 0.6 - cells * 0.8
base = np.array([0.016, 0.015, 0.015])
col = base[None, None, :] * (1 + 0.25 * grain[..., None] - 0.2 * cells[..., None])
save("Leather", srgb(col), h, 3.0, 0.5 + 0.12 * cells - 0.05 * grain, 0.0)

# ---------------------------------------------------------------- perforated leather
P = 24                                   # holes per row across the tile
pu, pv = xx * P, yy * P
row = np.floor(pv).astype(int)
pu = pu + 0.5 * (row % 2)                # staggered rows
du, dv = (pu % 1) - 0.5, (pv % 1) - 0.5
hole = np.clip(1 - np.sqrt(du ** 2 + dv ** 2) / 0.18, 0, 1)
hole = (hole > 0).astype(np.float32) * (0.6 + 0.4 * hole)
h2 = h - hole * 1.5
col2 = col * (1 - 0.85 * hole[..., None])
save("Perforated", srgb(col2), h2, 3.0, 0.55 + 0.3 * hole, 0.0)

# ---------------------------------------------------------------- alcantara
fuzz = fft_noise(0.4, lo=120, seed=5)
mott = fft_noise(2.0, lo=2, hi=20, seed=6)
h = fuzz * 0.5
lin = 0.035 * (1 + 0.15 * mott + 0.12 * fuzz)
col = np.stack([lin, lin, lin * 1.04], -1)
save("Alcantara", srgb(col), h, 1.5, 0.93, 0.0)

# ---------------------------------------------------------------- brushed aluminium
br = aniso_noise(1, 300, seed=7) * 0.7 + aniso_noise(1, 40, seed=8) * 0.3
lin = 0.55 + 0.06 * br
col = np.stack([lin, lin * 1.005, lin * 1.02], -1)
save("BrushedAlu", srgb(col), br * 0.3, 1.0, 0.28 + 0.08 * br, 1.0)

# ---------------------------------------------------------------- honeycomb grille mesh
H, R = 14, 16                            # hexagons across, hexagon rows (even, so it tiles)
X, Y = xx * H, yy * R
best1 = np.full((N, N), 9.0, np.float32)
best2 = np.full((N, N), 9.0, np.float32)
for dj in (-1, 0, 1, 2):
    jj = np.floor(Y) + dj
    for di in (-1, 0, 1, 2):
        ii = np.floor(X) + di + 0.5 * np.mod(jj, 2)
        d = np.sqrt((X - ii) ** 2 + ((Y - jj) * 0.866) ** 2)
        best2 = np.where(d < best1, best1, np.minimum(best2, d))
        best1 = np.minimum(best1, d)
web = np.clip(1 - (best2 - best1) / 0.09, 0, 1)   # 1 on the walls between cells
h = web
lin = 0.006 + 0.07 * web
col = np.stack([lin, lin, lin * 1.05], -1)
save("Honeycomb", srgb(col), h, 4.0, 0.45 + 0.35 * (1 - web), 0.7 * web)
print("tiles written to", OUT)
