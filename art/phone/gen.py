# Phone UI art via the ForgeGUI key pool (JustClips/Dev tools/forgegui.py).
# python3 art/phone/gen.py TAG [frame|wallpaper ...] -> raw/*.png, then proc.py -> out/
import sys, os, concurrent.futures as cf
sys.path.insert(0, "/home/user/dev/tools")
import forgegui
_wait = forgegui.wait
forgegui.wait = lambda job, kid, timeout=2400: _wait(job, kid, timeout)  # jobs can be slow
HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "raw")
JOBS = {
    "frame": ("mixed", 2,
        "A modern premium smartphone (newest iPhone Pro style, unbranded, no logo) seen straight from the front, "
        "perfectly upright and symmetrical, tall portrait shape about 9 by 19.5, thin even black bezels, "
        "rounded corners, polished dark natural titanium edge band with subtle metallic highlights, "
        "physical side buttons visible on the edges: action button and two volume buttons on the left edge, "
        "one long power button on the right edge. The screen is completely flat pure black (#000000), "
        "switched off, no reflections, no glare, no notch, no content, no text. Product UI cut-out, whole phone inside the frame."),
    "wallpaper2": ("thumbnail", 2,
        "Highly detailed premium smartphone lock screen wallpaper in the style of modern iOS default wallpapers (original art, not a copy): "
        "large soft glowing 3D shapes made of translucent frosted glass ribbons and petals folding over each other, layered depth, "
        "rich vivid colours (deep blue, violet, magenta, warm orange), fine light refraction, subtle grain, smooth gradients, "
        "dark background around them, crisp high resolution, studio lighting. The main shape is a tall vertical composition "
        "centred in the middle third of the image so it can be cropped to a tall phone screen. No text, no logo, no device, no UI."),
    "wallpaper": ("thumbnail", 1,
        "Abstract modern phone wallpaper art, smooth flowing glossy gradient waves, deep violet, midnight blue and "
        "warm orange-pink sunset glow, soft light, minimal, elegant, premium like a new flagship smartphone default wallpaper. "
        "No text, no logo, no objects, no people, the interesting part centred so it can be cropped to a tall portrait."),
}
TAG = sys.argv[1] if len(sys.argv) > 1 else "v1"
def run(name):
    t, n, p = JOBS[name]
    return name, forgegui.image(RAW, p, t, count=n, request_id=f"tulevo-phone-{name}-{TAG}")
with cf.ThreadPoolExecutor(2) as ex:
    for name, paths in ex.map(run, sys.argv[2:] or list(JOBS)):
        print(name, paths, flush=True)
