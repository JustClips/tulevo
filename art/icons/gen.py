# Inventory UI icons via the ForgeGUI key pool (JustClips/Dev tools/forgegui.py).
# Usage: python3 gen.py TAG [names...] -> raw/<Name>.png, then proc.py makes white masks in out/.
import sys, os, json, time, urllib.request, concurrent.futures as cf
sys.path.insert(0, "/home/user/dev/tools")
import forgegui
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw"); os.makedirs(RAW, exist_ok=True)
STYLE = ("Minimal modern game HUD icon, like the icons in a GTA roleplay server inventory screen. "
         "One single flat solid white glyph, clean simple silhouette, no outline, no shading, no gradient, no 3D, "
         "centred, filling most of the frame, transparent background. No text, no letters, no frame, no tile or circle behind it.")
ICONS = {
    "Heart": "a heart (health)",
    "Shield": "a shield (armor points)",
    "Vest": "a tactical body armor vest / plate carrier seen from the front, with shoulder straps and a few pouches",
    "Backpack": "a backpack seen from the front, with two shoulder straps and a front pocket",
    "Hands": "two open hands side by side, palms facing the viewer",
    "Wallet": "a closed leather wallet seen from the front, with a flap and a small clasp, a bank note peeking out the top",
    "Store": "a shopping cart seen from the side, with a handle, a basket made of a grid of bars and two wheels",
    "Players": "two people standing side by side, head and shoulders silhouettes, the one in front slightly larger",
    "BankCard": "a bank credit card seen from the front, a chip on the left and a magnetic stripe, card outline drawn with the inner area cut out so the details read",
}
TAG = sys.argv[1]
only = sys.argv[2:] or list(ICONS)

def one(name):
    path = os.path.join(RAW, name + ".png")
    if os.path.exists(path):
        return name, "cached"
    prompt = f"{STYLE} The icon: {ICONS[name]}."
    with forgegui.store(write=False) as d:
        keys = [k["key"] for k in forgegui.order(d, 1600)]
    for key in keys[:6]:
        args = {"request_id": f"tulevo-inv-{name.lower()}-{TAG}-{forgegui.key_id(key)}", "type": "gui_icon",
                "prompt": prompt, "count": 1}
        status, r = forgegui.attempt(key, "generation_gui", args)
        if status in ("empty", "invalid"):
            continue
        if status == "error":
            return name, f"error {json.dumps(r)[:300]}"
        st = r
        if r.get("status") in ("queued", "running", "pending", "processing"):
            for _ in range(8):
                try:
                    st = forgegui.wait(r["job_id"], forgegui.key_id(key)); break
                except Exception:
                    time.sleep(20)
        if st.get("status") != "succeeded":
            if "credits" in str(st.get("error")):
                continue
            return name, f"{st.get('status')}: {str(st.get('error'))[:300]}"
        arts = (st.get("result") or {}).get("artifacts", [])
        if not arts:
            return name, "no artifact"
        urllib.request.urlretrieve(arts[0]["url"], path)
        return name, "ok"
    return name, "no key"

with cf.ThreadPoolExecutor(3) as ex:
    for name, msg in ex.map(one, only):
        print(name, msg, flush=True)
