"""Small Blender kit shared by the city building scripts (motel, apartments, ...).

A building is a set of named parts; each part is one mesh with one material, so in Roblox it
becomes one MeshPart with one TextureID (tools/upload_textures.py). Parts named Light*/Lamp<n>/
Neon<Colour> get their glow in game from src/server/CityBuildings.server.luau.

Materials are either a flat colour (8x8 PNG) or a sheet drawn by a tools/*_textures.py script
(PIL) in <script dir>/tex/<Name>_Color.png, tiled in world space (tile=(u, v) studs) or mapped
with explicit UVs (printed signs, doors). Built in studs, 1 m = 3.6 studs, -Y = the front
(Roblox -Z), origin = ground centre.
"""
import bpy, bmesh, math, os, sys, json, shutil
import numpy as np
from mathutils import Vector, Matrix

M = 3.6


def args(default_out):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = next((a for a in argv if not a.startswith("--") and not a.replace(".", "").isdigit()), default_out)
    return {"out": out, "render": "--no-render" not in argv,
            "samples": int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 128,
            "res": float(argv[argv.index("--res") + 1]) if "--res" in argv else 1.0,
            # --face S builds the same building turned round (front to +Y / Roblox +Z, south) as <Name>_S,
            # because the LiveSync plugin places buildings without rotation
            "face": argv[argv.index("--face") + 1] if "--face" in argv else "N"}


def model_name(base, a):
    return base if a["face"] == "N" else f"{base}_{a['face']}"


class Kit:
    def __init__(self, name, out, texdir):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.name, self.out, self.texdir = name, out, texdir
        self.tex = os.path.join(out, "textures")
        self.ren = os.path.join(out, "renders")
        for d in (out, self.tex, self.ren):
            os.makedirs(d, exist_ok=True)
        self.mats = {}      # name -> dict(color image path, tile, explicit, emit)
        self.parts = {}     # part -> object
        self.bms = {}
        self.lamps = []

    # ------------------------------------------------------------ materials
    def _png(self, fname, rgb):
        h, w = rgb.shape[:2]
        img = bpy.data.images.new(fname, w, h, alpha=False)
        px = np.ones((h, w, 4), np.float32)
        px[..., :3] = rgb
        img.pixels.foreach_set(px[::-1].ravel())
        img.filepath_raw = os.path.join(self.tex, fname + ".png")
        img.file_format = 'PNG'
        img.save()
        return img

    def mat(self, name, color=None, sheet=None, rough=0.6, metal=0.0, tile=None, explicit=False, emit=0.0, alpha=False):
        """color=(r,g,b) for a flat colour, or sheet='X' for tex/X_Color.png (+ X_Roughness.png if there)."""
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        N, L = m.node_tree.nodes, m.node_tree.links
        b = N['Principled BSDF']
        if sheet:
            path = os.path.join(self.texdir, f"{sheet}_Color.png")
            img = bpy.data.images.load(path, check_existing=True)
            rp = os.path.join(self.texdir, f"{sheet}_Roughness.png")
            if os.path.exists(rp):
                r = N.new('ShaderNodeTexImage'); r.image = bpy.data.images.load(rp, check_existing=True)
                r.image.colorspace_settings.name = 'Non-Color'
                L.new(r.outputs['Color'], b.inputs['Roughness'])
            else:
                b.inputs['Roughness'].default_value = rough
            src = path
        else:
            img = self._png(name + "_Color", np.ones((8, 8, 3), np.float32) * np.array(color, np.float32))
            b.inputs['Roughness'].default_value = rough
            src = img.filepath_raw
        t = N.new('ShaderNodeTexImage'); t.image = img; t.extension = 'REPEAT'
        L.new(t.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Metallic'].default_value = metal
        if alpha:   # PNG alpha = see-through (graffiti, chain-link); Roblox MeshPart TextureID keeps it too
            L.new(t.outputs['Alpha'], b.inputs['Alpha'])
            try:
                m.surface_render_method = 'DITHERED'
            except Exception:
                pass
        if emit:
            L.new(t.outputs['Color'], b.inputs['Emission Color'])
            b.inputs['Emission Strength'].default_value = emit
        self.mats[name] = {"mat": m, "src": src, "tile": tile, "explicit": explicit}
        return m

    # ------------------------------------------------------------ geometry
    def bm(self, part, mat=None):
        if part not in self.bms:
            me = bpy.data.meshes.new(part)
            ob = bpy.data.objects.new(part, me)
            self.scene.collection.objects.link(ob)
            ob.data.materials.append(self.mats[mat or part]["mat"])
            ob["mat"] = mat or part
            self.parts[part] = ob
            self.bms[part] = bmesh.new()
            self.bms[part].loops.layers.uv.new("UVMap")
        return self.bms[part]

    def box(self, part, center, size, rz=0.0, mat=None):
        bm = self.bm(part, mat)
        r = bmesh.ops.create_cube(bm, size=1.0)
        mx = Matrix.Translation(Vector(center)) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Diagonal((*size, 1))
        bmesh.ops.transform(bm, matrix=mx, verts=r["verts"])

    def boxr(self, part, x0, x1, y0, y1, z0, z1, mat=None):
        """Box from ranges."""
        self.box(part, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)), mat=mat)

    def cyl(self, part, center, radius, depth, segs=12, axis='Z', r2=None, mat=None):
        rot = {'Z': Matrix.Identity(4), 'X': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'Y': Matrix.Rotation(math.pi / 2, 4, 'X')}[axis]
        bmesh.ops.create_cone(self.bm(part, mat), cap_ends=True, segments=segs, radius1=radius,
                              radius2=radius if r2 is None else r2, depth=depth, matrix=Matrix.Translation(Vector(center)) @ rot)

    def cyl_along(self, part, a, b, radius, segs=10, mat=None):
        a, b = Vector(a), Vector(b)
        d = b - a
        rot = d.normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm(part, mat), cap_ends=True, segments=segs, radius1=radius, radius2=radius, depth=d.length,
                              matrix=Matrix.Translation((a + b) / 2) @ rot)

    def quad(self, part, corners, uvs=((0, 0), (1, 0), (1, 1), (0, 1)), mat=None):
        bm = self.bm(part, mat)
        uv = bm.loops.layers.uv.active
        f = bm.faces.new([bm.verts.new(c) for c in corners])
        for l, t in zip(f.loops, uvs):
            l[uv].uv = t
        return f

    def face_y(self, part, cx, y, z0, w, h, facing=-1, uvs=((0, 0), (1, 0), (1, 1), (0, 1)), mat=None):
        xs = (cx - w / 2, cx + w / 2) if facing < 0 else (cx + w / 2, cx - w / 2)
        return self.quad(part, [(xs[0], y, z0), (xs[1], y, z0), (xs[1], y, z0 + h), (xs[0], y, z0 + h)], uvs, mat)

    def face_x(self, part, x, cy, z0, w, h, facing=1, uvs=((0, 0), (1, 0), (1, 1), (0, 1)), mat=None):
        ys = (cy - w / 2, cy + w / 2) if facing > 0 else (cy + w / 2, cy - w / 2)
        return self.quad(part, [(x, ys[0], z0), (x, ys[1], z0), (x, ys[1], z0 + h), (x, ys[0], z0 + h)], uvs, mat)

    def lamp(self, center, size):
        """A Lamp<n> part (downward SurfaceLight + light shaft in game)."""
        name = f"Lamp{len(self.lamps) + 1}"
        self.bm(name, "Light")
        self.box(name, center, size)
        self.lamps.append(name)
        return name

    def shrub(self, x, y, z, s, rng, part="Shrub", subdiv=1):
        bm = self.bm(part)
        r = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=s)
        for v in r["verts"]:
            v.co = Vector((x + v.co.x * rng.uniform(0.85, 1.15), y + v.co.y * rng.uniform(0.85, 1.15), z + s * 0.6 + v.co.z * 0.75))

    def palm(self, x, y, z, h, lean, rng):
        pts = [Vector((x + lean[0] * M * t * t, y + lean[1] * M * t * t, z + h * t)) for t in [i / 14 for i in range(15)]]
        for i in range(14):
            self.cyl_along("Trunk", pts[i], pts[i + 1], 0.2 * M * (1 - 0.35 * i / 14) * (1.08 if i % 2 else 1.0), segs=8)
        top = pts[-1]
        self.cyl("Trunk", tuple(top + Vector((0, 0, 0.2 * M))), 0.2 * M, 0.5 * M, segs=8, r2=0.1 * M)
        bm = self.bm("Palm")
        for f in range(11):
            a = f / 11 * math.tau + rng.uniform(-0.15, 0.15)
            d = Vector((math.cos(a), math.sin(a), 0)); side = Vector((-d.y, d.x, 0))
            L, lift = rng.uniform(3.6, 4.4) * M, rng.uniform(0.3, 0.9)
            rows = []
            for s_ in range(8):
                t = s_ / 7
                c = top + Vector((0, 0, 0.35 * M)) + d * (L * t) + Vector((0, 0, (lift * t - 1.6 * t * t) * M))
                w = 0.55 * M * math.sin(math.pi * min(1.0, t * 1.15 + 0.05))
                dip = Vector((0, 0, -0.18 * w))
                rows.append((c + side * w + dip, c, c - side * w + dip))
            for s_ in range(7):
                for k in range(2):
                    a1, b1, a2, b2 = rows[s_][k], rows[s_][k + 1], rows[s_ + 1][k], rows[s_ + 1][k + 1]
                    bm.faces.new([bm.verts.new(p) for p in (a1, b1, b2, a2)])
                    bm.faces.new([bm.verts.new(p - Vector((0, 0, 0.02))) for p in (a2, b2, b1, a1)])

    # ------------------------------------------------------------ facade detail
    GLASS = ("GlassA", "GlassB", "GlassC", "GlassD", "GlassE", "GlassF")

    def facade_mats(self, frame=(0.93, 0.92, 0.89), sill=(0.80, 0.78, 0.73)):
        """Frame / Sill / WinIron colours + the Glass* sheets (tex_kit.glass_set) if the building has them."""
        for name, col, rough, metal in (("Frame", frame, 0.45, 0.2), ("Sill", sill, 0.8, 0.0), ("WinIron", (0.03, 0.03, 0.035), 0.45, 0.6),
                                        ("Pipe", (0.86, 0.85, 0.82), 0.5, 0.2), ("Meter", (0.55, 0.57, 0.58), 0.4, 0.7)):
            if name not in self.mats:
                self.mat(name, color=col, rough=rough, metal=metal)
        for g in self.GLASS + ("GlassFrost",):
            if g not in self.mats and os.path.exists(os.path.join(self.texdir, f"{g}_Color.png")):
                self.mat(g, sheet=g, explicit=True)

    def _wbox(self, part, ax, plane, facing, a, da, out, z, sa, so, sz):
        if ax == "y":
            self.box(part, (a + da, plane + facing * out, z), (sa, so, sz))
        else:
            self.box(part, (plane + facing * out, a + da, z), (so, sa, sz))

    def window3d(self, ax, plane, facing, a, z0, w, h, glass=None, depth=0.12 * M, fw=0.07 * M, mull=1, transom=False,
                 bars=False, sill=True, head=True, frame="Frame"):
        """A real window on a wall plane: framed glass with depth, mullions, sill and head trim,
        optional iron security bars. ax 'y' = wall plane y=plane (a along x), 'x' = plane x (a along y);
        facing = the side it is seen from (+1/-1). glass = a Glass* part (None: a random one)."""
        glass = glass or self.GLASS[(hash((round(a, 1), round(z0, 1), round(plane, 1))) % len(self.GLASS))]
        if glass in self.mats:
            if ax == "y":
                self.face_y(glass, a, plane + 0.03 * facing, z0, w, h, facing=facing)
            else:
                self.face_x(glass, plane + 0.03 * facing, a, z0, w, h, facing=facing)
        B = lambda part, da, out, z, sa, so, sz: self._wbox(part, ax, plane, facing, a, da, out, z, sa, so, sz)
        # frame: 4 sides standing out of the wall
        B(frame, 0, depth / 2, z0 + h + fw / 2, w + 2 * fw, depth, fw)
        B(frame, 0, depth / 2, z0 - fw / 2, w + 2 * fw, depth, fw)
        for s_ in (-1, 1):
            B(frame, s_ * (w / 2 + fw / 2), depth / 2, z0 + h / 2, fw, depth, h)
        for k in range(1, mull + 1):                           # vertical mullions (sash split)
            B(frame, -w / 2 + k * w / (mull + 1), depth * 0.3, z0 + h / 2, fw * 0.6, depth * 0.6, h)
        if transom:
            B(frame, 0, depth * 0.3, z0 + h * 0.72, w, depth * 0.6, fw * 0.6)
        if sill:
            B("Sill", 0, (depth + 0.1 * M) / 2, z0 - fw - 0.035 * M, w + 2 * fw + 0.2 * M, depth + 0.1 * M, 0.07 * M)
        if head:
            B("Sill", 0, 0.04 * M, z0 + h + fw + 0.06 * M, w + 2 * fw + 0.24 * M, 0.08 * M, 0.12 * M)
        if bars:
            n = max(2, int(w / (0.13 * M)))
            for i in range(n + 1):
                B("WinIron", -w / 2 + i * w / n, depth + 0.05 * M, z0 + h / 2, 0.03 * M, 0.03 * M, h + 0.1 * M)
            for z in (z0 + 0.12 * h, z0 + h * 0.5, z0 + 0.88 * h):
                B("WinIron", 0, depth + 0.05 * M, z, w + 0.1 * M, 0.04 * M, 0.04 * M)

    def downpipe(self, x, y, z0, z1, r=0.05 * M):
        self.cyl("Pipe", (x, y, (z0 + z1) / 2), r, z1 - z0, segs=8)
        for z in [z0 + 0.4 * M + k * 1.6 * M for k in range(int((z1 - z0 - 0.4 * M) / (1.6 * M)) + 1)]:
            self.cyl("Pipe", (x, y, z), r * 1.35, 0.06 * M, segs=8)

    def meter_box(self, ax, plane, facing, a, z):
        self._wbox("Meter", ax, plane, facing, a, 0, 0.1 * M, z, 0.45 * M, 0.2 * M, 0.6 * M)
        self._wbox("WinIron", ax, plane, facing, a, 0, 0.21 * M, z + 0.08 * M, 0.2 * M, 0.02 * M, 0.2 * M)

    # ------------------------------------------------------------ finish + export
    def finish(self, keep_normals=("Palm",), face="N"):
        for name, bm in self.bms.items():
            info = self.mats[self.parts[name]["mat"]]
            uv = bm.loops.layers.uv.active
            bm.normal_update()
            if not info["explicit"]:
                tile = info["tile"]
                for f in bm.faces:
                    n = f.normal
                    ax = max(range(3), key=lambda i: abs(n[i]))
                    for l in f.loops:
                        co = l.vert.co
                        if not tile:
                            l[uv].uv = (0.5, 0.5)
                            continue
                        if ax == 2:
                            u, v = co.x, co.y
                        elif ax == 0:
                            u, v = co.y * (1 if n.x > 0 else -1), co.z
                        else:
                            u, v = co.x * (-1 if n.y > 0 else 1), co.z
                        l[uv].uv = (u / tile[0], v / tile[1])
                if name not in keep_normals:
                    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(self.parts[name].data)
            bm.free()
            turn = {"N": 0, "S": math.pi, "E": -math.pi / 2, "W": math.pi / 2}[face]
            if turn:
                self.parts[name].data.transform(Matrix.Rotation(turn, 4, 'Z'))
            for p in self.parts[name].data.polygons:
                p.use_smooth = False

    def export(self):
        meta = {"name": self.name, "units": "studs", "scale": 1, "parts": {}, "lamps": self.lamps, "textures": {}}
        total = 0
        for name, ob in self.parts.items():
            vs = [v.co for v in ob.data.vertices]
            tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
            assert tris < 20000, f"{name} has {tris} tris (Roblox limit 20k)"
            meta["parts"][name] = {"tris": tris, "min": [round(min(v[i] for v in vs), 2) for i in range(3)],
                                   "max": [round(max(v[i] for v in vs), 2) for i in range(3)]}
            total += tris
            src = self.mats[ob["mat"]]["src"]
            dst = os.path.join(self.tex, os.path.basename(src))
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copyfile(src, dst)
            meta["textures"][name] = os.path.basename(src)
        print(self.name, "parts", len(self.parts), "tris", total)
        json.dump(meta, open(os.path.join(self.out, "meta.json"), "w"), indent=1)
        for o in self.scene.objects:
            o.select_set(o.name in self.parts)
        bpy.ops.export_scene.gltf(filepath=os.path.join(self.out, f"{self.name}.glb"), export_format='GLB', use_selection=True,
                                  export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
                                  export_materials='EXPORT', export_image_format='AUTO')
        return meta

    # ------------------------------------------------------------ renders
    def render_setup(self, samples, res, ground=4000):
        sc = self.scene
        sc.render.engine = 'CYCLES'
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            for t in ('OPTIX', 'CUDA'):
                try:
                    prefs.compute_device_type = t
                    prefs.get_devices()
                    if any(d.type == t for d in prefs.devices):
                        break
                except Exception:
                    continue
            for d in prefs.devices:
                d.use = True
            sc.cycles.device = 'GPU'
        except Exception as e:
            print("GPU setup failed, using CPU:", e)
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.exposure = -0.4
        self.res = res
        w = bpy.data.worlds.new("Sky"); w.use_nodes = True; sc.world = w
        N, L = w.node_tree.nodes, w.node_tree.links
        bg = N['Background']
        try:
            sky = N.new('ShaderNodeTexSky')
            for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING', 'HOSEK_WILKIE'):
                try:
                    sky.sky_type = t
                    break
                except Exception:
                    pass
            try:
                sky.sun_elevation, sky.sun_rotation = math.radians(30), math.radians(215)
            except Exception:
                pass
            L.new(sky.outputs['Color'], bg.inputs['Color'])
            bg.inputs['Strength'].default_value = 0.35
        except Exception as e:
            print("sky texture unavailable:", e)
        sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
        sun.data.energy, sun.data.angle = 3.0, math.radians(1.0)
        sun.rotation_euler = (math.radians(58), 0, math.radians(125))
        sc.collection.objects.link(sun)
        m = bpy.data.materials.new("Ground"); m.use_nodes = True
        m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.05, 0.05, 0.05, 1)
        bpy.ops.mesh.primitive_plane_add(size=ground, location=(0, 0, -0.05)); bpy.context.object.data.materials.append(m)
        self.cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(self.cam); sc.camera = self.cam

    def shot(self, name, loc, target, lens=30, size=(1600, 900)):
        cam = self.cam
        cam.location = loc
        cam.rotation_euler = (Vector(target) - Vector(loc)).normalized().to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens, cam.data.clip_end = lens, 10000
        self.scene.render.resolution_x, self.scene.render.resolution_y = int(size[0] * self.res), int(size[1] * self.res)
        self.scene.render.filepath = os.path.join(self.ren, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name)
