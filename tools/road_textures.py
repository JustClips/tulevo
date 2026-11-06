"""Makes the city street textures in art/road/tex (one road type: worn city asphalt, GTA LA style).

  python3 tools/road_textures.py

Sources are CC0 photo scans, downloaded once into art/road/src (git-ignored):
  ambientCG Asphalt025C (base asphalt), ambientCG ManholeCover006, Poly Haven asphalt_track (patch fill),
  Poly Haven brushed_concrete (sidewalks).

Outputs (every image: x = along the road, y = across it, top of the image = the road's left edge):
  StreetColor/Normal/Rough   1024 tiling MaterialVariant maps (16 studs per tile)
  Lanes2/4/6                 tiling wear for 2/4/6-lane roads: oil strip in the lane middles, polished
                             wheel paths, dusty gutters (88 studs along, full width across)
  Tar1..4                    tar-sealed crack lines ("tar snakes"), 44 x 44 studs
  Crack1..3, Gator1..2       open cracks / alligator cracking, 22 x 22 studs
  Patch1..3                  sawcut repair patches with sealed edges
  Stain1..3                  oil drips, 8 x 8 studs
  Grime1..3                  big soft dark/dusty blotches, 44 x 66 studs
  Paint, PaintV              worn chipped road paint, tiles along the line (6 studs); V = turned 90
  Manhole                    round iron cover with its asphalt ring
  WalkColor/Normal/Rough     sidewalk concrete MaterialVariant maps (Poly Haven brushed_concrete):
                             4 x 4 scored 5 ft slabs per tile (21.6 studs), per-slab tone, cracks
  KerbTop, KerbFace, Gum     kerb edge band, kerb's vertical face, gum spots
art/road/textures.json maps these names to the png paths for tools/upload_textures.py.
"""
import io
import json
import os
import urllib.request
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "art", "road", "src")
TEX = os.path.join(ROOT, "art", "road", "tex")
rng = np.random.default_rng(7)

ACG = "https://ambientcg.com/get?file={}_2K-PNG.zip"
PH = "https://dl.polyhaven.org/file/ph-assets/Textures/png/2k/asphalt_track/asphalt_track_{}_2k.png"


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "tulevo-road-textures"})).read()


def fetch():
    os.makedirs(SRC, exist_ok=True)
    for aid in ("Asphalt025C", "ManholeCover006"):
        if not os.path.exists(os.path.join(SRC, aid)):
            data = get(ACG.format(aid))
            zipfile.ZipFile(io.BytesIO(data)).extractall(os.path.join(SRC, aid))
    for kind in ("diff", "rough"):
        p = os.path.join(SRC, f"asphalt_track_{kind}.png")
        if not os.path.exists(p):
            open(p, "wb").write(get(PH.format(kind)))
    for kind in ("diff", "nor_gl", "rough"):
        p = os.path.join(SRC, f"brushed_concrete_{kind}.png")
        if not os.path.exists(p):
            open(p, "wb").write(get(PH.format(kind).replace("asphalt_track", "brushed_concrete")))


def load(path, mode="RGB", size=None):
    im = Image.open(path).convert(mode)
    if size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255


def save(name, arr, mode=None):
    arr = np.clip(arr * 255 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(arr, mode).save(os.path.join(TEX, name + ".png"), optimize=True)
    return name


def noise(h, w, scale, octaves=4, seed=None):
    """Tileable fractal noise 0..1 (FFT-filtered white noise; scale = feature size in px)."""
    g = np.random.default_rng(seed if seed is not None else rng.integers(1 << 30))
    out = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    for o in range(octaves):
        s = scale / (2 ** o)
        filt = np.exp(-(f * s) ** 2 * 2)
        n = np.real(np.fft.ifft2(np.fft.fft2(g.standard_normal((h, w))) * filt))
        n = (n - n.mean()) / (n.std() + 1e-6)
        out += n * amp
        total += amp
        amp *= 0.5
    out /= total
    return np.clip(0.5 + out * 0.25, 0, 1)


def blur(a, r):
    """Wrap-around gaussian blur (keeps tiling)."""
    h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    filt = np.exp(-2 * (np.pi * r) ** 2 * (fx * fx + fy * fy))
    if a.ndim == 3:
        filt = filt[..., None]
    return np.real(np.fft.ifft2(np.fft.fft2(a, axes=(0, 1)) * filt, axes=(0, 1))).astype(np.float32)


def smooth(a, lo, hi):
    t = np.clip((a - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def edge_fade(h, w, margin):
    y = np.minimum(np.arange(h), np.arange(h)[::-1])[:, None] / margin
    x = np.minimum(np.arange(w), np.arange(w)[::-1])[None, :] / margin
    return smooth(np.minimum(np.minimum(x, 1), np.minimum(y, 1)), 0, 1)


def rgba(color, alpha):
    h, w = alpha.shape
    c = np.broadcast_to(np.asarray(color, np.float32), (h, w, 3)) if np.ndim(color) == 1 else color
    return np.dstack([c, np.clip(alpha, 0, 1)])


# ---------------------------------------------------------------- base asphalt
def base():
    d = os.path.join(SRC, "Asphalt025C")
    col = load(os.path.join(d, "Asphalt025C_2K-PNG_Color.png"), size=(1024, 1024))
    nor = load(os.path.join(d, "Asphalt025C_2K-PNG_NormalGL.png"), size=(1024, 1024))
    rough = load(os.path.join(d, "Asphalt025C_2K-PNG_Roughness.png"), "L", size=(1024, 1024))
    ao = load(os.path.join(d, "Asphalt025C_2K-PNG_AmbientOcclusion.png"), "L", size=(1024, 1024))
    # strip the scan's big light/dark clouds (they'd repeat every tile); the overlays add large-scale wear
    col = col - blur(col, 40) + col.mean(axis=(0, 1))
    rough = rough - blur(rough, 40) + rough.mean()
    # lift to a mid-dark LA street grey, a touch cool, keep the stones' contrast
    lum = col.mean(axis=2, keepdims=True)
    col = lum + (col - lum) * 0.55
    col = np.power(col, 0.78) * np.array([1.02, 1.03, 1.08]) * 1.12
    col *= (0.75 + 0.25 * ao[..., None])
    # very soft tileable tone drift inside the tile so it doesn't read as flat
    col *= (0.96 + 0.08 * noise(1024, 1024, 180, 2))[..., None]
    save("StreetColor", col)
    # normals a bit stronger so the aggregate catches light
    n = nor * 2 - 1
    n[..., :2] *= 1.35
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    save("StreetNormal", n * 0.5 + 0.5)
    r = 0.80 + (rough - rough.mean()) * 1.4 - (1 - ao) * 0.1
    save("StreetRough", np.clip(r, 0.55, 0.97), "L")


# ---------------------------------------------------------------- drawing helpers
def walk(start, heading, length, step, wiggle, rng_):
    """A meandering path: list of (x, y)."""
    pts = [np.array(start, float)]
    a = heading
    turn = 0.0
    for _ in range(int(length / step)):
        turn = turn * 0.8 + rng_.normal(0, wiggle)
        a += turn
        a = heading + np.clip(a - heading, -0.6, 0.6)
        pts.append(pts[-1] + step * np.array([np.cos(a), np.sin(a)]))
    return pts


def stroke(draw, pts, width_fn, fill=255):
    for i, p in enumerate(pts):
        r = width_fn(i / max(1, len(pts) - 1)) / 2
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=fill)


def taper(w0, jitter, rng_):
    k = rng_.uniform(0, 6.28)
    f1, f2 = rng_.uniform(9, 17), rng_.uniform(29, 47)
    return lambda t: max(0.6, w0 * (0.35 + 0.65 * np.sin(np.pi * t) ** 0.35) * (1 + jitter * 0.6 * np.sin(t * f1 + k) + jitter * 0.4 * np.sin(t * f2 + k * 2)))


def mask_from(draw_fn, size, ss=2, blur=0.0):
    im = Image.new("L", (size[0] * ss, size[1] * ss), 0)
    draw_fn(ImageDraw.Draw(im), ss)
    im = im.resize(size, Image.LANCZOS)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im).astype(np.float32) / 255


TAR = np.array([0.07, 0.07, 0.075])


# ---------------------------------------------------------------- tar snakes (44 x 44 studs)
def tar(i):
    g = np.random.default_rng(100 + i)
    S = 1024
    px = S / 44

    def draw(d, ss):
        lines = []
        # longitudinal: along a lane joint or wheel path
        for _ in range(g.integers(1, 3)):
            y = g.choice([11, 16.5, 22, 27.5, 33]) * px + g.normal(0, 1.5 * px)
            x0 = g.uniform(0.02, 0.3) * S
            lines.append(walk((x0, y), g.choice([0, np.pi]) if x0 > S / 2 else 0, g.uniform(0.4, 0.9) * S, 4, 0.02, g))
        # transverse: across the road (thermal crack) with a branch
        for _ in range(g.integers(0, 3)):
            x = g.uniform(0.15, 0.85) * S
            p = walk((x, g.uniform(0, 0.15) * S), np.pi / 2 + g.normal(0, 0.15), g.uniform(0.5, 0.95) * S, 4, 0.035, g)
            lines.append(p)
            if g.random() < 0.6:
                k = g.integers(len(p) // 4, 3 * len(p) // 4)
                lines.append(walk(p[k], g.choice([0.4, -0.4, 2.7]) + np.pi / 2 * g.choice([0, 1]), g.uniform(0.1, 0.3) * S, 4, 0.05, g))
        for pts in lines:
            pts = [q * ss for q in pts]
            stroke(d, pts, taper(g.uniform(9, 14) * ss, 0.55, g))

    m = mask_from(draw, (S, S), blur=0.6)
    a = m * (0.7 + 0.2 * noise(S, S, 20, 3)) * edge_fade(S, S, 30)
    col = TAR[None, None, :] * (0.85 + 0.3 * noise(S, S, 8, 2))[..., None]
    return save(f"Tar{i}", rgba(col, a))


# ---------------------------------------------------------------- open cracks (22 x 22 studs)
def crack(i):
    g = np.random.default_rng(200 + i)
    S = 1024

    def draw(d, ss):
        start = (g.uniform(0.05, 0.3) * S, g.uniform(0.3, 0.7) * S)
        trunk = walk(start, g.normal(0, 0.4), g.uniform(0.6, 0.9) * S, 3, 0.06, g)
        branches = [trunk]
        for _ in range(g.integers(3, 7)):
            src = branches[g.integers(len(branches))]
            k = g.integers(0, len(src))
            branches.append(walk(src[k], g.uniform(-2.2, 2.2), g.uniform(0.08, 0.35) * S, 3, 0.08, g))
        for j, pts in enumerate(branches):
            stroke(d, [q * ss for q in pts], taper((3.2 if j == 0 else 2.0) * ss, 0.5, g))

    m = mask_from(draw, (S, S))
    halo = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))).astype(np.float32) / 255
    dark = np.array([0.03, 0.03, 0.03])
    dust = np.array([0.42, 0.41, 0.39])
    w = np.clip(m * 1.5, 0, 1)[..., None]
    col = dark * w + dust * (1 - w)
    a = np.maximum(m * 0.92, np.clip(halo * 1.2, 0, 1) * 0.16) * edge_fade(S, S, 40)
    return save(f"Crack{i}", rgba(col, a))


def gator(i):
    """Alligator cracking: a blob of small jagged cells (Voronoi edges) with some ravelled bits."""
    g = np.random.default_rng(300 + i)
    S = 1024
    blob = smooth(noise(S, S, 260, 3, seed=301 + i) * edge_fade(S, S, 260), 0.35, 0.55)
    pts = g.uniform(0, S, (140, 2))
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    jx = (noise(S, S, 25, 2, seed=310 + i) - 0.5) * 40
    jy = (noise(S, S, 25, 2, seed=320 + i) - 0.5) * 40
    X, Y = xx + jx, yy + jy
    d1 = np.full((S, S), 1e9, np.float32)
    d2 = np.full((S, S), 1e9, np.float32)
    for p in pts:
        dd = np.hypot(X - p[0], Y - p[1])
        d2 = np.minimum(d2, np.maximum(d1, dd))
        d1 = np.minimum(d1, dd)
    edge = 1 - smooth(d2 - d1, 0.5, 3.5)
    ravel = smooth(noise(S, S, 40, 3, seed=330 + i), 0.68, 0.8) * blob
    a = np.clip(edge * blob * 0.95 + ravel * 0.55 + blob * 0.12, 0, 1)
    col = np.array([0.05, 0.05, 0.05])[None, None, :] * (1 - ravel[..., None]) + np.array([0.18, 0.17, 0.16]) * ravel[..., None]
    return save(f"Gator{i}", rgba(col, a))


# ---------------------------------------------------------------- repair patches
def patch(i):
    g = np.random.default_rng(400 + i)
    W, H = 1024, 768
    diff = load(os.path.join(SRC, "asphalt_track_diff.png"), size=(1024, 1024))
    oy = g.integers(0, 1024 - H)
    fill = np.roll(diff, g.integers(0, 1024), axis=1)[oy:oy + H]
    tone = [1.19, 1.55, 1.04][i - 1]  # about 0.85x / 1.12x / 0.78x the street's brightness
    lum = fill.mean(axis=2, keepdims=True)
    fill = np.power(np.clip(lum + (fill - lum) * 0.2, 0, 1), 0.75) * tone * np.array([1.0, 1.02, 1.07])
    fill *= (0.9 + 0.2 * noise(H, W, 120, 2, seed=410 + i))[..., None]
    m = 24  # margin for the seam
    corners = [(m + g.uniform(-6, 6), m + g.uniform(-6, 6)), (W - m + g.uniform(-6, 6), m + g.uniform(-6, 6)),
               (W - m + g.uniform(-6, 6), H - m + g.uniform(-6, 6)), (m + g.uniform(-6, 6), H - m + g.uniform(-6, 6))]

    def body(d, ss):
        d.polygon([(x * ss, y * ss) for x, y in corners], fill=255)

    def seam(d, ss):
        c = [(x * ss, y * ss) for x, y in corners]
        for k in range(4):
            a_, b_ = np.array(c[k]), np.array(c[(k + 1) % 4])
            n = int(np.linalg.norm(b_ - a_) / (3 * ss))
            pts = [a_ + (b_ - a_) * t + g.normal(0, 1.2 * ss, 2) for t in np.linspace(0, 1, n)]
            stroke(d, pts, taper(g.uniform(5, 8) * ss, 0.4, g))

    bm = mask_from(body, (W, H), blur=0.7)
    sm = mask_from(seam, (W, H), blur=0.8)
    col = fill * (1 - sm[..., None]) + TAR * sm[..., None]
    a = np.clip(bm + sm * 0.9, 0, 1)
    if i == 2:  # an old patch: faded with its own little cracks
        cm = mask_from(lambda d, ss: [stroke(d, [q * ss for q in walk((g.uniform(100, 900), g.uniform(100, 650)), g.uniform(0, 6.28), 260, 3, 0.07, g)], taper(2.2 * ss, 0.5, g)) for _ in range(4)], (W, H))
        col = col * (1 - cm[..., None] * 0.85)
    return save(f"Patch{i}", rgba(col, a))


# ---------------------------------------------------------------- oil stains (8 x 8 studs)
def stain(i):
    g = np.random.default_rng(500 + i)
    S = 512

    def draw(d, ss):
        cx, cy = S / 2, S / 2
        for _ in range(g.integers(6, 16)):
            x, y = cx + g.normal(0, 70), cy + g.normal(0, 45)
            r = g.uniform(6, 34)
            d.ellipse([(x - r * 1.3) * ss, (y - r) * ss, (x + r * 1.3) * ss, (y + r) * ss], fill=int(g.uniform(90, 255)))

    m = mask_from(draw, (S, S), blur=6)
    a = np.clip(m * (0.5 + 0.5 * noise(S, S, 30, 3)), 0, 1) * 0.7 * edge_fade(S, S, 60)
    col = np.array([0.06, 0.055, 0.05])
    return save(f"Stain{i}", rgba(col, a))


# ---------------------------------------------------------------- big soft blotches (44 x 66 studs)
def grime(i):
    S = 1024
    n = noise(S, S, 220, 4, seed=600 + i)
    fade = edge_fade(S, S, 220)
    darkm = smooth(n, 0.55, 0.78) * fade
    lightm = smooth(1 - n, 0.6, 0.8) * fade
    speck = smooth(noise(S, S, 3, 1, seed=610 + i), 0.72, 0.8) * lightm
    dark = np.array([0.06, 0.065, 0.07])
    light = np.array([0.55, 0.53, 0.5])
    w = (darkm / (darkm + lightm + 1e-6))[..., None]
    col = dark * w + light * (1 - w)
    a = darkm * 0.42 + lightm * 0.22 + speck * 0.25
    return save(f"Grime{i}", rgba(col, a))


# ---------------------------------------------------------------- lane wear (tiles along the road)
def lanes(n):
    W, H = 1024, 128 * n  # 88 studs along, n * 11 studs across
    sy = H / (n * 11)
    y = (np.arange(H) / sy)[:, None]  # studs from the left edge
    along = noise(H, W, 90, 3, seed=700 + n)
    oil = np.zeros((H, W), np.float32)
    wheel = np.zeros((H, W), np.float32)
    for k in range(n):
        c = (k + 0.5) * 11
        oil = np.maximum(oil, np.exp(-((y - c) / 1.1) ** 2))
        for o in (-3.2, 3.2):
            wheel = np.maximum(wheel, np.exp(-((y - c - o) / 0.9) ** 2))
    width = n * 11
    gutter = np.maximum(np.exp(-(y / 1.3) ** 2), np.exp(-((width - y) / 1.3) ** 2))
    oil_a = oil * smooth(along, 0.3, 0.7) * 0.32 + oil * smooth(noise(H, W, 6, 2, seed=710 + n), 0.62, 0.75) * 0.35
    wheel_a = wheel * (0.12 + 0.08 * along)
    dust = gutter * (0.35 + 0.25 * noise(H, W, 40, 3, seed=720 + n))
    debris = gutter * smooth(noise(H, W, 2.5, 1, seed=730 + n), 0.7, 0.78) * 0.6
    dk = (oil_a + wheel_a)[..., None]
    lt = (dust + debris)[..., None]
    dark = np.array([0.045, 0.045, 0.05])
    light = np.array([0.5, 0.47, 0.42])
    col = (dark * dk + light * lt) / (dk + lt + 1e-6)
    a = np.clip(oil_a + wheel_a + dust + debris, 0, 0.75)
    return save(f"Lanes{n}", rgba(col, a))


# ---------------------------------------------------------------- road paint (tiles along a line)
def paint():
    W, H = 1024, 64  # 6 studs along, the 0.4-stud line width across (about the same px per stud both ways)
    chip = noise(H, W, 10, 4, seed=800)
    big = noise(H, W, 120, 2, seed=801)
    edge = np.minimum(np.arange(H), np.arange(H)[::-1])[:, None] / 6 + (noise(H, W, 4, 2, seed=802) - 0.5) * 3
    a = smooth(edge, 0.3, 1.1) * smooth(chip + (big - 0.5) * 0.5, 0.22, 0.34) * (0.82 + 0.15 * big)
    col = np.array([0.95, 0.95, 0.93])[None, None, :] * (0.88 + 0.12 * noise(H, W, 6, 2, seed=803))[..., None]
    save("PaintV", np.transpose(rgba(col, a), (1, 0, 2)))  # same paint for lines whose length runs along Z
    return save("Paint", rgba(col, a))


# ---------------------------------------------------------------- manhole
def manhole():
    d = os.path.join(SRC, "ManholeCover006")
    S = 512
    col = load(os.path.join(d, "ManholeCover006_2K-PNG_Color.png"), size=(S, S))
    op = load(os.path.join(d, "ManholeCover006_2K-PNG_Opacity.png"), "L", size=(S, S))
    lum = col.mean(axis=2, keepdims=True)
    col = (lum + (col - lum) * 0.45) * 0.85  # less rust orange, worn dark iron
    yy, xx = np.mgrid[0:S, 0:S]
    r = np.hypot(xx - S / 2, yy - S / 2) / (S / 2)
    ring = smooth(r, 0.9, 0.94) * (1 - smooth(r, 0.985, 1.0))
    a = np.maximum(op * (1 - smooth(r, 0.93, 0.96)), ring * 0.9)
    col = col * (1 - ring[..., None]) + TAR * ring[..., None]
    return save("Manhole", rgba(col, a))


# ---------------------------------------------------------------- sidewalks
PANEL_PX = 256  # 4 x 4 scored panels per 1024 tile; tile = 21.6 studs, panel = 5.4 studs (5 ft)


def sidewalk():
    """LA-style broom-finished concrete slabs: per-panel tone, scored joints, stains, a few cracked panels."""
    g = np.random.default_rng(900)
    S = 1024
    col = load(os.path.join(SRC, "brushed_concrete_diff.png"), size=(S, S))
    nor = load(os.path.join(SRC, "brushed_concrete_nor_gl.png"), size=(S, S))
    rough = load(os.path.join(SRC, "brushed_concrete_rough.png"), "L", size=(S, S))
    col = col - blur(col, 50) + col.mean(axis=(0, 1))
    lum = col.mean(axis=2, keepdims=True)
    col = lum + (col - lum) * 0.25  # nearly grey, a hint of warm
    lum = col.mean(axis=2, keepdims=True)
    col = lum.mean() + (col - lum.mean()) * 0.55  # softer trowel marks
    col = col / col.mean() * 0.56 * np.array([1.0, 0.99, 0.96])
    yy, xx = np.mgrid[0:S, 0:S]
    pi, pj = yy // PANEL_PX, xx // PANEL_PX
    tone = g.uniform(0.9, 1.08, (4, 4))
    col *= tone[pi, pj][..., None]
    # dirt that collects toward joints + random blotches per panel
    dy = np.minimum(yy % PANEL_PX, PANEL_PX - yy % PANEL_PX)
    dx = np.minimum(xx % PANEL_PX, PANEL_PX - xx % PANEL_PX)
    dj = np.minimum(dx, dy).astype(np.float32)
    col *= (1 - 0.12 * np.exp(-dj / 18))[..., None]
    blot = smooth(noise(S, S, 70, 3, seed=901), 0.62, 0.8)
    col *= (1 - 0.1 * blot)[..., None]
    # scored joints: a groove 4 px wide with dark grime
    groove = np.exp(-(dj / 2.2) ** 2)
    col = col * (1 - groove[..., None] * 0.7)
    # cracks in a few panels
    cm = mask_from(lambda d, ss: [stroke(d, [q * ss for q in walk(
        (pj0 * PANEL_PX + g.uniform(0, 1) * PANEL_PX, pi0 * PANEL_PX + g.choice([2, PANEL_PX - 2])),
        g.uniform(1.0, 2.1) * (1 if g.random() < 0.5 else -1), PANEL_PX * g.uniform(0.6, 1.2), 3, 0.07, g)],
        taper(2.4 * ss, 0.5, g)) for pi0, pj0 in g.integers(0, 4, (3, 2))], (S, S))
    col *= (1 - cm[..., None] * 0.7)
    save("WalkColor", np.clip(col, 0, 1))
    # normals: the scan's broom grain + groove slopes from a height map
    h = -groove * 3.0 - cm * 1.5
    gx = np.roll(h, -1, 1) - np.roll(h, 1, 1)
    gy = np.roll(h, -1, 0) - np.roll(h, 1, 0)
    n = nor * 2 - 1
    n[..., 0] -= gx * 0.5
    n[..., 1] += gy * 0.5
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    save("WalkNormal", n * 0.5 + 0.5)
    r = 0.82 + (rough - rough.mean()) * 1.2 + groove * 0.1 - blot * 0.06
    save("WalkRough", np.clip(r, 0.6, 0.98), "L")


def kerb():
    """Kerb top edge band (1.2 studs across, 8 along): worn, chipped lip with gutter grime on the road side.
    y = 0 is the road side."""
    W, H = 1024, 160
    y = np.arange(H)[:, None] / H
    n = noise(H, W, 30, 3, seed=910)
    lip = np.exp(-(y / 0.18) ** 2)  # the rounded worn edge right at the road
    grime = np.exp(-(y / 0.08) ** 2) * (0.5 + 0.5 * noise(H, W, 12, 2, seed=911))
    chips = smooth(noise(H, W, 5, 2, seed=912), 0.66, 0.74) * np.exp(-(y / 0.25) ** 2)
    scuff = smooth(noise(H, W, 60, 2, seed=913), 0.62, 0.72) * np.exp(-(y / 0.35) ** 2)  # black tyre scuffs
    light = np.array([0.66, 0.65, 0.62])
    dark = np.array([0.09, 0.085, 0.08])
    w_dark = np.clip(grime * 0.8 + chips * 0.9 + scuff * 0.3, 0, 1)
    w_light = lip * 0.45 * (0.6 + 0.4 * n)
    col = (light * w_light[..., None] + dark * w_dark[..., None]) / (w_light + w_dark + 1e-6)[..., None]
    a = np.clip(w_light + w_dark, 0, 0.9)
    return save("KerbTop", rgba(col, a))


def kerb_face():
    """The kerb's vertical face (8 studs along, 0.6 tall): grimy concrete, darker toward the road surface,
    drip streaks and tyre scuffs. Opaque, top of the image = top of the kerb."""
    W, H = 1024, 80
    y = np.arange(H)[:, None] / H
    base = np.array([0.5, 0.49, 0.46]) * (0.85 + 0.3 * noise(H, W, 20, 3, seed=920))[..., None]
    streak = smooth(noise(H, W * 1, 6, 2, seed=921), 0.55, 0.75)
    base *= (1 - 0.35 * streak * y)[..., None]
    base *= (1 - 0.55 * y ** 2)[..., None]
    scuff = smooth(noise(H, W, 30, 2, seed=922), 0.68, 0.8)
    base *= (1 - 0.35 * scuff)[..., None]
    return save("KerbFace", np.dstack([base, np.ones((H, W))]))


def gum():
    """Gum spots and small stains for sidewalk tops (8 x 8 studs)."""
    g = np.random.default_rng(930)
    S = 512

    def draw(d, ss):
        for _ in range(70):
            x, y = g.uniform(30, S - 30, 2)
            r = g.uniform(2.5, 6)
            d.ellipse([(x - r) * ss, (y - r * 0.9) * ss, (x + r) * ss, (y + r * 0.9) * ss], fill=int(g.uniform(120, 255)))

    m = mask_from(draw, (S, S), blur=0.8)
    a = m * 0.75
    col = np.array([0.2, 0.2, 0.2])
    return save("Gum", rgba(col, a))


def main():
    os.makedirs(TEX, exist_ok=True)
    fetch()
    base()
    names = ["StreetColor", "StreetNormal", "StreetRough"]
    names += [lanes(n) for n in (2, 4, 6)]
    names += [tar(i) for i in range(1, 5)]
    names += [crack(i) for i in range(1, 4)]
    names += [gator(i) for i in range(1, 3)]
    names += [patch(i) for i in range(1, 4)]
    names += [stain(i) for i in range(1, 4)]
    names += [grime(i) for i in range(1, 4)]
    names += [paint(), "PaintV", manhole()]
    sidewalk()
    names += ["WalkColor", "WalkNormal", "WalkRough", kerb(), kerb_face(), gum()]
    tj = {n: f"art/road/tex/{n}.png" for n in names}
    json.dump(tj, open(os.path.join(ROOT, "art", "road", "textures.json"), "w"), indent=1)
    print(f"wrote {len(names)} textures to {TEX}")


if __name__ == "__main__":
    main()
