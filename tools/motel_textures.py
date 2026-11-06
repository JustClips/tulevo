"""Texture sheets for the Palmview Motel (original name and design), PIL only.

  python3 tools/motel_textures.py   ->  art/blender/motel/tex/*.png

Room fronts (door + window + curtains), room number plates, stucco, shingle roof band,
parking asphalt, the neon pylon sign, office glass, pool water, back wall, ice/vending.
"""
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from tex_kit import FONT_B, FONT_R, fit_text, font, grime, noise_tile, saver, scratches, text_c, glass_set, stucco as stucco_tex  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
save = saver(os.path.join(ROOT, "art", "blender", "motel", "tex"))
r = random.Random(11)

CREAM = (226, 214, 190)
TURQ = (30, 150, 150)
CORAL = (226, 104, 84)
PINK = (255, 70, 170)


def stucco():
    # 512 px sprayed stucco with cracks + patches (tex_kit.stucco), tiled every 3.5 m
    save("Stucco", grime(stucco_tex(CREAM, 1), 0.1, 2), 230)
    glass_set(save, seed=910)


def room_front():
    W, H = 640, 512          # one room bay: 4.0 m x 3.2 m
    im = noise_tile(W, H, CREAM, 9, 3)
    d = ImageDraw.Draw(im)
    # door (turquoise) with frame, peephole, handle, kick plate
    dx0, dx1, dy0 = 70, 220, 70
    d.rectangle([dx0 - 10, dy0 - 10, dx1 + 10, H], fill=(245, 242, 232))
    d.rectangle([dx0, dy0, dx1, H], fill=TURQ)
    for k in range(3):
        d.rectangle([dx0 + 18, dy0 + 24 + k * 130, dx1 - 18, dy0 + 120 + k * 130], outline=(20, 120, 120), width=4)
    d.ellipse([dx0 + 68, dy0 + 120, dx0 + 82, dy0 + 134], fill=(30, 30, 30))
    d.rectangle([dx1 - 34, 300, dx1 - 22, 330], fill=(200, 170, 90))
    d.rectangle([dx0 + 6, H - 40, dx1 - 6, H - 6], fill=(170, 160, 140))
    # window: aluminium frame, two panes, warm curtains half drawn
    wx0, wx1, wy0, wy1 = 300, 590, 120, 330
    d.rectangle([wx0 - 12, wy0 - 12, wx1 + 12, wy1 + 20], fill=(245, 242, 232))
    d.rectangle([wx0, wy0, wx1, wy1], fill=(60, 66, 74))
    lit = r.random() < 0.5
    d.rectangle([wx0 + 6, wy0 + 6, wx1 - 6, wy1 - 6], fill=(250, 214, 150) if lit else (48, 54, 62))
    for x0, x1 in ((wx0 + 6, wx0 + 110), (wx1 - 110, wx1 - 6)):
        for k in range(x0, x1, 12):
            d.rectangle([k, wy0 + 6, k + 8, wy1 - 6], fill=(196, 92, 70))
            d.line([(k + 10, wy0 + 6), (k + 10, wy1 - 6)], fill=(150, 64, 50), width=2)
    d.polygon([(wx0 + 6, wy0 + 6), (wx0 + 70, wy0 + 6), (wx0 + 6, wy0 + 90)], fill=(255, 255, 255))
    d.rectangle([(wx0 + wx1) // 2 - 4, wy0, (wx0 + wx1) // 2 + 4, wy1], fill=(170, 172, 176))
    d.rectangle([wx0 - 16, wy1 + 12, wx1 + 16, wy1 + 26], fill=(205, 200, 188))      # sill
    # "no smoking" sticker + do not disturb hanger on the knob
    d.ellipse([dx0 + 40, dy0 + 40, dx0 + 70, dy0 + 70], fill=(245, 245, 245), outline=(200, 30, 30), width=4)
    d.line([(dx0 + 44, dy0 + 66), (dx0 + 66, dy0 + 44)], fill=(200, 30, 30), width=4)
    im = grime(im, 0.18, 4)
    rough = Image.new("L", (W, H), 225)
    ImageDraw.Draw(rough).rectangle([wx0, wy0, wx1, wy1], fill=20)
    save("RoomFront", im, rough)


def room_numbers():
    W, H = 512, 256          # 8 x 4 plates: 101-116, 201-216
    im = Image.new("RGB", (W, H), (40, 40, 42))
    d = ImageDraw.Draw(im)
    for k in range(32):
        x, y = (k % 8) * 64, (k // 8) * 64
        n = (101 + k) if k < 16 else (201 + k - 16)
        d.rectangle([x + 3, y + 3, x + 61, y + 61], fill=(196, 160, 70))
        d.rectangle([x + 7, y + 7, x + 57, y + 57], outline=(140, 110, 40), width=2)
        text_c(d, (x + 32, y + 33), str(n), font(FONT_B, 22), (40, 30, 20))
    save("RoomNumbers", im, 80)


def back_wall():
    W, H = 640, 512
    im = noise_tile(W, H, (214, 202, 178), 9, 5)
    d = ImageDraw.Draw(im)
    for x0 in (120, 420):     # small frosted bathroom windows
        d.rectangle([x0 - 8, 92, x0 + 98, 192], fill=(240, 236, 226))
        d.rectangle([x0, 100, x0 + 90, 184], fill=(186, 196, 200))
        d.line([(x0 + 45, 100), (x0 + 45, 184)], fill=(150, 152, 156), width=4)
    d.rectangle([300, 40, 330, 60], fill=(120, 120, 120))     # vent
    im = grime(im, 0.25, 6)
    save("BackWall", im, 235)


def roof_tile():
    W = 256
    im = Image.new("RGB", (W, W), (150, 66, 40))
    d = ImageDraw.Draw(im)
    rows = 8
    for j in range(rows):
        y = j * W // rows
        off = (W // 16) if j % 2 else 0
        for i in range(-1, 9):
            x = i * W // 8 + off
            c = r.randint(-18, 14)
            d.rectangle([x + 1, y + 1, x + W // 8 - 2, y + W // rows - 2], fill=(160 + c, 72 + c // 2, 44 + c // 3))
            d.line([(x + 1, y + W // rows - 3), (x + W // 8 - 2, y + W // rows - 3)], fill=(96, 40, 24), width=3)
    im = grime(im, 0.25, 7)
    save("RoofTile", im, 200)


def asphalt():
    W = 512
    im = noise_tile(W, W, (52, 53, 55), 12, 8, 0.6)
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(6):
        x, y, s = r.randint(0, W), r.randint(0, W), r.randint(20, 70)
        d.ellipse([x - s, y - s // 2, x + s, y + s // 2], fill=(20, 20, 22, 70))
    for _ in range(5):  # tar crack seals
        x, y = r.randint(0, W), r.randint(0, W)
        pts = [(x, y)]
        for _ in range(8):
            x += r.randint(-30, 30); y += r.randint(10, 40)
            pts.append((x, y))
        d.line(pts, fill=(18, 18, 18, 200), width=3)
    im = im.filter(ImageFilter.GaussianBlur(0.4))
    save("Asphalt", im, 235)


def motel_sign():
    W, H = 512, 1024         # pylon sign cabinet, 1:2
    im = Image.new("RGB", (W, H), TURQ)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, H], outline=(250, 240, 220), width=18)
    # sunset disc + palm silhouette
    d.ellipse([140, 60, 372, 292], fill=(250, 150, 60))
    for k, c in enumerate(((250, 120, 60), (240, 90, 80), (220, 70, 110))):
        d.rectangle([140, 200 + k * 26, 372, 212 + k * 26], fill=TURQ)
    d.line([(256, 300), (262, 170)], fill=(20, 60, 60), width=10)
    for a, b in (((262, 170), (190, 150)), ((262, 170), (330, 140)), ((262, 170), (220, 205)), ((262, 170), (316, 205)), ((262, 170), (262, 120))):
        d.line([a, b], fill=(20, 60, 60), width=12)
    fit_text(d, (W / 2, 370), "PALMVIEW", FONT_B, W - 70, 96, (255, 245, 225))
    d.rectangle([60, 430, W - 60, 436], fill=(250, 150, 60))
    fit_text(d, (W / 2, 520), "MOTEL", FONT_B, W - 90, 150, PINK)
    fit_text(d, (W / 2, 640), "COLOR TV  ·  POOL", FONT_B, W - 90, 40, (255, 245, 225))
    fit_text(d, (W / 2, 690), "FREE WI-FI  ·  A/C", FONT_B, W - 90, 40, (255, 245, 225))
    fit_text(d, (W / 2, 760), "WEEKLY RATES", FONT_R, W - 90, 36, (250, 200, 120))
    d.rectangle([60, 830, W - 60, 960], fill=(30, 20, 26))
    fit_text(d, (W / 2, 895), "VACANCY", FONT_B, W - 150, 76, (255, 60, 80))
    im = grime(im, 0.12, 9, streaks=False)
    save("MotelSign", im, 90)


def office_glass():
    W, H = 1024, 512
    g = Image.linear_gradient("L").resize((W, H))
    im = Image.merge("RGB", [g.point(lambda v, a=a, b=b: int(a + (b - a) * v / 255)) for a, b in ((120, 70), (130, 80), (130, 86))])
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([300, 300, 760, 420], fill=(150, 96, 60, 220))            # reception desk
    d.rectangle([300, 290, 760, 306], fill=(220, 210, 190, 230))
    d.rectangle([420, 120, 640, 230], fill=(240, 236, 226, 160))          # rates board
    text_c(d, (530, 150), "RATES", font(FONT_B, 28), (40, 40, 40, 230))
    for k in range(3):
        d.rectangle([440, 175 + k * 16, 620, 183 + k * 16], fill=(80, 80, 80, 180))
    d.rectangle([80, 330, 220, 420], fill=(60, 120, 60, 200))             # plant
    d.rounded_rectangle([780, 150, 960, 230], 10, fill=(20, 10, 14, 230))  # OPEN sign
    text_c(d, (870, 190), "OPEN", font(FONT_B, 46), (255, 60, 110))
    for i in range(5):
        x = int(i * W / 4)
        d.rectangle([x - 8, 0, x + 8, H], fill=(36, 36, 38, 255))
    d.rectangle([0, 0, W, 12], fill=(36, 36, 38, 255)); d.rectangle([0, H - 16, W, H], fill=(36, 36, 38, 255))
    text_c(d, (W // 8 * 5, 470), "PLEASE RING BELL", font(FONT_B, 18), (240, 240, 240, 200))
    rough = Image.new("L", (W, H), 15)
    save("OfficeGlass", im, rough)


def office_sign():
    W, H = 1024, 160
    im = Image.new("RGB", (W, H), (245, 240, 228))
    d = ImageDraw.Draw(im)
    fit_text(d, (W / 2, H / 2 + 4), "OFFICE  ·  CHECK-IN", FONT_B, W - 80, 100, TURQ)
    d.rectangle([0, H - 14, W, H], fill=CORAL)
    save("OfficeSign", grime(im, 0.1, 12, streaks=False), 90)


def ice_sign():
    W, H = 512, 128
    im = Image.new("RGB", (W, H), (30, 110, 170))
    d = ImageDraw.Draw(im)
    fit_text(d, (W / 2, H / 2), "ICE  ·  VENDING", FONT_B, W - 40, 70, (255, 255, 255))
    save("IceSign", grime(im, 0.1, 13, streaks=False), 90)


def soda():
    W, H = 256, 512
    im = Image.new("RGB", (W, H), (30, 90, 170))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 70], fill=(20, 60, 130))
    fit_text(d, (W / 2, 38), "COOL SIP", FONT_B, W - 30, 36, (255, 255, 255))
    d.rectangle([16, 84, 176, 380], fill=(16, 18, 22))
    cols = ((220, 40, 40), (250, 200, 40), (60, 170, 80), (240, 240, 240), (240, 120, 30), (150, 80, 200))
    for j in range(6):
        for i in range(6):
            x, y = 24 + i * 25, 100 + j * 47
            d.rounded_rectangle([x, y, x + 18, y + 32], 4, fill=cols[(i * 2 + j) % 6])
        d.rectangle([20, 136 + j * 47, 172, 139 + j * 47], fill=(110, 110, 116))
    d.rectangle([188, 84, 244, 380], fill=(24, 24, 28))
    for k in range(6):
        d.rectangle([198, 96 + k * 34, 234, 120 + k * 34], fill=(220, 220, 220))
    d.rectangle([30, 404, 226, 470], fill=(12, 12, 14))
    save("Soda", grime(im, 0.12, 14), 70)


def ice_machine():
    W, H = 256, 512
    im = Image.new("RGB", (W, H), (220, 224, 228))
    d = ImageDraw.Draw(im)
    d.rectangle([20, 40, W - 20, 120], fill=(30, 110, 170))
    fit_text(d, (W / 2, 80), "ICE", FONT_B, W - 60, 60, (255, 255, 255))
    d.rectangle([40, 200, W - 40, 380], fill=(160, 166, 172))
    d.rectangle([60, 220, W - 60, 360], fill=(110, 116, 122))
    for y in range(400, 500, 12):
        d.line([(20, y), (W - 20, y)], fill=(140, 144, 150), width=4)
    save("IceMachine", scratches(grime(im, 0.15, 15), 80, 16, (160, 160, 160), 60), 90)


def pool_water():
    W = 512
    im = Image.new("RGB", (W, W), (40, 170, 210))
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(140):  # caustic ripples
        x, y, s = r.randint(0, W), r.randint(0, W), r.randint(10, 40)
        d.arc([x - s, y - s // 2, x + s, y + s // 2], r.randint(0, 180), r.randint(180, 360), fill=(200, 245, 255, 120), width=2)
    d.rectangle([W // 2 - 6, 0, W // 2 + 6, W], fill=(20, 70, 140, 160))   # lane line on the floor
    save("PoolWater", im.filter(ImageFilter.GaussianBlur(0.8)), 10)


def concrete():
    im = grime(noise_tile(256, 256, (170, 168, 160), 12, 17), 0.2, 18)
    d = ImageDraw.Draw(im)
    d.line([(0, 0), (256, 0)], fill=(120, 118, 112), width=3)
    d.line([(0, 0), (0, 256)], fill=(120, 118, 112), width=3)
    save("Concrete", im, 220)


def ac_unit():
    W, H = 256, 128
    im = Image.new("RGB", (W, H), (214, 212, 204))
    d = ImageDraw.Draw(im)
    for x in range(16, 160, 10):
        d.rectangle([x, 20, x + 5, H - 20], fill=(120, 120, 118))
    d.rectangle([180, 30, 236, 60], fill=(90, 90, 90))
    d.ellipse([196, 76, 220, 100], fill=(150, 150, 150))
    save("AcUnit", grime(im, 0.25, 19), 150)


for fn in (stucco, room_front, room_numbers, back_wall, roof_tile, asphalt, motel_sign, office_glass, office_sign,
           ice_sign, soda, ice_machine, pool_water, concrete, ac_unit):
    fn()
