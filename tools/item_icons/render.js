/*
  Renders crisp, transparent inventory icons from the item models (art/models/<Model>/<Model>.glb)
  into art/items/out/<ItemId>.png. tools/upload_icons.py --set items uploads them and writes
  src/shared/ItemIconIds.luau, which the inventory window shows instead of a live 3D view
  (ViewportFrames have no anti-aliasing, so they look pixelated).

    cd tools/item_icons && npm install && node render.js [ItemId ...]

  Uses the pre-installed Chromium (Playwright) with three.js. Each icon is drawn at the item's
  cell shape (Cells wide x tall, 160 px a cell: about the size a cell takes on a
  1440p-4K screen, so Roblox never has to shrink an icon much), viewed from VIEW.
*/
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.join(ROOT, "art", "items", "out");

// ItemId -> model, cells (wide x tall, matching the item's Cells), view = direction from the
// model toward the camera (glTF axes: +Y up), roll = degrees the picture turns
const ITEMS = {
	CarbineRifle: { model: "CarbineRifle", cells: [4, 2], view: [-1, 0.08, 0], roll: 0 },
	ArmorVest: { model: "ArmorVest", cells: [2, 2], view: [0.3, 0.15, 1], roll: 0 },
	Mead: { model: "Mead", cells: [1, 2], view: [0.35, 0.25, 1], roll: 0 },
	Chaser: { model: "Chaser", cells: [1, 2], view: [0.35, 0.25, 1], roll: 0 },
	FirstAidKit: { model: "FirstAidKit", cells: [2, 2], view: [0.45, 0.5, 1], roll: 0 },
};

const PAGE = `<!doctype html><html><body style="margin:0;background:transparent">
<script type="importmap">{"imports":{"three":"/three/build/three.module.js","three/addons/":"/three/examples/jsm/"}}</script>
<script type="module">
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const SS = 2; // supersampling on top of MSAA
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setClearColor(0x000000, 0);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.15;
document.body.appendChild(renderer.domElement);
const pmrem = new THREE.PMREMGenerator(renderer);
const envMap = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

window.renderIcon = async ({ url, w, h, view, roll, pad }) => {
	const gltf = await new GLTFLoader().loadAsync(url);
	const scene = new THREE.Scene();
	scene.environment = envMap;
	scene.environmentIntensity = 0.9;
	const model = gltf.scene;
	scene.add(model);
	model.updateMatrixWorld(true);

	// lights on top of the soft room light: key from top left, rim from behind
	const key = new THREE.DirectionalLight(0xffffff, 1.6);
	const rim = new THREE.DirectionalLight(0xffffff, 0.8);
	scene.add(key, rim, key.target, rim.target);

	// camera axes: looking along -dir, up as close to +Y as possible, then rolled
	const dir = new THREE.Vector3(...view).normalize();
	let up = new THREE.Vector3(0, 1, 0);
	if (Math.abs(dir.dot(up)) > 0.99) up = new THREE.Vector3(0, 0, -1);
	const right = new THREE.Vector3().crossVectors(up, dir).normalize();
	up = new THREE.Vector3().crossVectors(dir, right).normalize();
	const r = THREE.MathUtils.degToRad(roll || 0);
	const R = right.clone().multiplyScalar(Math.cos(r)).addScaledVector(up, Math.sin(r));
	const U = up.clone().multiplyScalar(Math.cos(r)).addScaledVector(right, -Math.sin(r));

	// exact extents over every vertex, seen along dir
	let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity, z0 = Infinity, z1 = -Infinity;
	const v = new THREE.Vector3();
	model.traverse((o) => {
		if (!o.isMesh) return;
		const p = o.geometry.attributes.position;
		for (let i = 0; i < p.count; i++) {
			v.fromBufferAttribute(p, i).applyMatrix4(o.matrixWorld);
			const x = v.dot(R), y = v.dot(U), z = v.dot(dir);
			x0 = Math.min(x0, x); x1 = Math.max(x1, x);
			y0 = Math.min(y0, y); y1 = Math.max(y1, y);
			z0 = Math.min(z0, z); z1 = Math.max(z1, z);
		}
	});
	const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
	let hw = (x1 - x0) / 2, hh = (y1 - y0) / 2;
	const aspect = w / h;
	if (hw / hh > aspect) hh = hw / aspect; else hw = hh * aspect;
	hw *= 1 + pad; hh *= 1 + pad;
	const depth = z1 - z0;
	const cam = new THREE.OrthographicCamera(-hw, hw, hh, -hh, 0.01, depth * 4 + 1);
	const centre = R.clone().multiplyScalar(cx).addScaledVector(U, cy);
	cam.position.copy(centre).addScaledVector(dir, z1 + depth + 0.5);
	cam.up.copy(U);
	cam.lookAt(centre);

	const size = Math.max(hw, hh) * 4;
	key.position.copy(centre).addScaledVector(dir, size).addScaledVector(U, size).addScaledVector(R, -size * 0.6);
	key.target.position.copy(centre);
	rim.position.copy(centre).addScaledVector(dir, -size).addScaledVector(U, size * 0.5).addScaledVector(R, size);
	rim.target.position.copy(centre);

	renderer.setSize(w * SS, h * SS, false);
	renderer.render(scene, cam);

	// downsample in steps of 2 for a clean result
	let src = renderer.domElement;
	let cw = w * SS, ch = h * SS;
	while (cw > w) {
		cw = Math.max(w, cw / 2); ch = Math.max(h, ch / 2);
		const c = document.createElement("canvas");
		c.width = cw; c.height = ch;
		const g = c.getContext("2d");
		g.imageSmoothingEnabled = true;
		g.imageSmoothingQuality = "high";
		g.drawImage(src, 0, 0, cw, ch);
		src = c;
	}
	return src.toDataURL("image/png");
};
window.ready = true;
</script></body></html>`;

function serve() {
	const types = { ".js": "text/javascript", ".glb": "model/gltf-binary", ".html": "text/html" };
	const server = http.createServer((req, res) => {
		const u = decodeURIComponent(req.url.split("?")[0]);
		let file;
		if (u === "/") {
			res.writeHead(200, { "Content-Type": "text/html" });
			return res.end(PAGE);
		} else if (u.startsWith("/three/")) {
			file = path.join(__dirname, "node_modules", u);
		} else if (u.startsWith("/models/")) {
			file = path.join(ROOT, "art", u);
		}
		if (!file || !fs.existsSync(file)) {
			res.writeHead(404);
			return res.end();
		}
		res.writeHead(200, { "Content-Type": types[path.extname(file)] || "application/octet-stream" });
		fs.createReadStream(file).pipe(res);
	});
	return new Promise((ok) => server.listen(0, "127.0.0.1", () => ok(server)));
}

(async () => {
	const want = process.argv.slice(2);
	const ids = want.length ? want : Object.keys(ITEMS);
	fs.mkdirSync(OUT, { recursive: true });
	const server = await serve();
	const base = `http://127.0.0.1:${server.address().port}`;
	const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
	const page = await browser.newPage();
	page.on("pageerror", (e) => console.error("page error:", e.message));
	await page.goto(base + "/");
	await page.waitForFunction(() => window.ready === true);
	for (const id of ids) {
		const it = ITEMS[id];
		if (!it) {
			console.error(`unknown item ${id}`);
			continue;
		}
		let [cw, ch] = it.cells;
		const scale = Math.min(160, 1024 / Math.max(cw, ch));
		const w = Math.round(cw * scale), h = Math.round(ch * scale);
		const data = await page.evaluate((a) => window.renderIcon(a), {
			url: `/models/${it.model}/${it.model}.glb`, w, h, view: it.view, roll: it.roll, pad: it.pad ?? 0.08,
		});
		const file = path.join(OUT, `${id}.png`);
		fs.writeFileSync(file, Buffer.from(data.split(",")[1], "base64"));
		console.log(`${id}: ${w}x${h} -> ${path.relative(ROOT, file)}`);
	}
	await browser.close();
	server.close();
})();
