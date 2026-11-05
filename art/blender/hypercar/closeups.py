"""Close-up review renders of the built model (tail lamp, driver's view, wheel).

  blender --background --python closeups.py [-- hypercar.blend]
"""
import bpy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

name = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "hypercar_model.blend"
bpy.ops.wm.open_mainfile(filepath=os.path.join(C.OUT, name))
scene = bpy.context.scene
C.setup_studio(scene)
ren = os.path.join(C.OUT, "renders")
VIEWS = {
    "tail": ((1.9, 3.6, 1.05), (0.62, 2.2, 0.78), 50),
    "headlamp": ((1.25, -3.3, 1.05), (0.58, -2.12, 0.47), 60),
    "nose": ((-1.6, -3.9, 0.75), (0.0, -2.0, 0.40), 40),
    "windscreen": ((-2.0, -2.2, 1.6), (0.0, -0.6, 0.95), 40),
    "rear_low": ((0.0, 6.0, 0.9), (0, 2.2, 0.6), 45),
    "driver": ((0.38, 0.30, 1.08), (0.38, -0.45, 0.66), 28),
    "dash": ((-0.15, 0.25, 1.15), (0.1, -0.55, 0.62), 24),
}
for k, (loc, tgt, lens) in VIEWS.items():
    C.render(scene, os.path.join(ren, f"close_{k}.png"), loc, tgt, lens, samples=48, res=(1280, 720))
