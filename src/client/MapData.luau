-- Map data shared by the radar and the full map.
--
-- Tag map parts in Studio and they show up on both:
--   Road     light grey line (roads are also what the GPS drives along)
--   Building grey block on the dark ground
--   Water    dark blue
--   Park     dark green
-- A tag works on a Part (its footprint), a Model (its bounding box) or a
-- Folder (every part inside). Untagged things don't show.
--
-- Road network for the GPS: every Road piece is a straight line along its
-- long side. Roads that cross, or whose end touches another road, are joined.
-- Bends/curves = several straight pieces that touch or overlap at their ends
-- (a Model or Folder tagged Road uses each of its parts). Joins are drawn
-- round, so short pieces make a smooth curve.
local CollectionService = game:GetService("CollectionService")

local MapData = {}

-- Colors follow the radar look: dark ground, low-contrast building blocks,
-- light roads. Thin shrinks a road's width when drawn.
MapData.LAYERS = {
	Park = { Name = "Park", Color = Color3.fromRGB(58, 68, 56), Y = 0.1 },
	Water = { Name = "Water", Color = Color3.fromRGB(52, 70, 86), Y = 0.2 },
	Building = { Name = "Building", Color = Color3.fromRGB(56, 58, 59), Y = 0.3, Inset = 1 },
	Road = { Name = "Road", Color = Color3.fromRGB(150, 152, 152), Y = 0.4, Thin = 0.5 },
}
MapData.GROUND = Color3.fromRGB(40, 42, 42)
MapData.ROUTE = Color3.fromRGB(160, 92, 230)

-- Fires after the tagged map changed (shapes and roads were re-read).
local changed = Instance.new("BindableEvent")
MapData.Changed = changed.Event

local function flat(v: Vector3): Vector3
	local f = Vector3.new(v.X, 0, v.Z)
	return if f.Magnitude > 1e-3 then f.Unit else Vector3.new(0, 0, -1)
end
MapData.flat = flat

-- Ground footprint of a box: centre, forward/right ground axes and sizes along them.
local function footprint(cf: CFrame, size: Vector3)
	local look, right = flat(cf.LookVector), flat(cf.RightVector)
	local function along(axis: Vector3)
		return math.abs(cf.RightVector:Dot(axis)) * size.X
			+ math.abs(cf.UpVector:Dot(axis)) * size.Y
			+ math.abs(cf.LookVector:Dot(axis)) * size.Z
	end
	return Vector3.new(cf.X, 0, cf.Z), look, right, along(right), along(look)
end

-- Roads use every part on its own (a Model of road pieces can bend);
-- other tags use a Model's bounding box.
local function eachBox(inst: Instance, perPart: boolean, fn: (CFrame, Vector3) -> ())
	if inst:IsA("BasePart") then
		fn(inst.CFrame, inst.Size)
	elseif inst:IsA("Model") and not perPart then
		local cf, size = inst:GetBoundingBox()
		fn(cf, size)
	else
		for _, d in inst:GetDescendants() do
			if d:IsA("BasePart") then
				fn(d.CFrame, d.Size)
			end
		end
	end
end

-- Shapes -------------------------------------------------------------------
type Shape = { pos: Vector3, look: Vector3, sx: number, sz: number, layer: any }
local shapes: { Shape } = {}

-- Roads (GPS graph) ------------------------------------------------------
type Seg = { a: Vector3, b: Vector3, dir: Vector3, len: number, width: number, entries: { { t: number, id: number } } }
local segs: { Seg } = {}
local nodes: { Vector3 } = {}
local adj: { { [number]: number } } = {}

local function addNode(p: Vector3): number
	for i, n in nodes do
		if (n - p).Magnitude < 1.5 then
			return i
		end
	end
	table.insert(nodes, p)
	adj[#nodes] = {}
	return #nodes
end

-- Drawn road pieces: one per graph edge, with its road width.
local edges: { { a: number, b: number, width: number } } = {}

local function link(i: number, j: number, width: number)
	if i ~= j then
		local d = (nodes[i] - nodes[j]).Magnitude
		if not adj[i][j] then
			table.insert(edges, { a = i, b = j, width = width })
		end
		adj[i][j] = d
		adj[j][i] = d
	end
end

local function closestOn(s: Seg, p: Vector3): (number, Vector3)
	local t = math.clamp((p - s.a):Dot(s.dir), 0, s.len)
	return t, s.a + s.dir * t
end

local function cross(v: Vector3, w: Vector3): number
	return v.X * w.Z - v.Z * w.X
end

local function buildGraph()
	table.clear(nodes)
	table.clear(adj)
	table.clear(edges)
	-- Each segment's own entries: both ends.
	for _, s in segs do
		s.entries = {
			{ t = 0, id = addNode(s.a) },
			{ t = s.len, id = addNode(s.b) },
		}
	end
	for i = 1, #segs do
		local s1 = segs[i]
		for j = i + 1, #segs do
			local s2 = segs[j]
			-- Centre lines cross (also T-junctions that stop at the other road's edge).
			local denom = cross(s1.dir, s2.dir)
			if math.abs(denom) > 1e-3 then
				local d = s2.a - s1.a
				local t = cross(d, s2.dir) / denom
				local u = cross(d, s1.dir) / denom
				local tol1, tol2 = s2.width / 2 + 2, s1.width / 2 + 2
				if t >= -tol1 and t <= s1.len + tol1 and u >= -tol2 and u <= s2.len + tol2 then
					local tc, uc = math.clamp(t, 0, s1.len), math.clamp(u, 0, s2.len)
					local id1 = addNode(s1.a + s1.dir * tc)
					local id2 = addNode(s2.a + s2.dir * uc)
					table.insert(s1.entries, { t = tc, id = id1 })
					table.insert(s2.entries, { t = uc, id = id2 })
					link(id1, id2, math.min(s1.width, s2.width))
				end
			end
			-- An end of one road touching the other (chains and overlaps).
			for _, pair in { { s1, s2 }, { s2, s1 } } do
				local from, to = pair[1], pair[2]
				for _, e in { from.a, from.b } do
					local t, q = closestOn(to, e)
					if (q - e).Magnitude <= math.max(to.width, from.width) / 2 + 1 then
						local idq = addNode(q)
						table.insert(to.entries, { t = t, id = idq })
						link(addNode(e), idq, from.width)
					end
				end
			end
		end
	end
	for _, s in segs do
		table.sort(s.entries, function(x, y)
			return x.t < y.t
		end)
		for k = 2, #s.entries do
			link(s.entries[k - 1].id, s.entries[k].id, s.width)
		end
	end
end

local function read()
	table.clear(shapes)
	table.clear(segs)
	for tag, layer in MapData.LAYERS do
		for _, inst in CollectionService:GetTagged(tag) do
			if inst:IsDescendantOf(workspace) then
				eachBox(inst, tag == "Road", function(cf, size)
					local pos, look, right, sx, sz = footprint(cf, size)
					table.insert(shapes, { pos = pos, look = look, sx = sx, sz = sz, layer = layer })
					if tag == "Road" then
						-- A road runs along the part's Z (front) unless it's clearly
						-- longer along X. Short curve pieces can be wider than long,
						-- so "longest side" alone would turn them sideways.
						-- Attribute RoadAxis = "X" or "Z" forces it.
						local axis = inst:GetAttribute("RoadAxis")
						local useX = if axis == "X" then true elseif axis == "Z" then false else sx > sz * 2
						local dir, len, width
						if useX then
							dir, len, width = right, sx, sz
						else
							dir, len, width = look, sz, sx
						end
						table.insert(segs, {
							a = pos - dir * len / 2,
							b = pos + dir * len / 2,
							dir = dir,
							len = len,
							width = width,
							entries = {},
						})
					end
				end)
			end
		end
	end
	buildGraph()
	changed:Fire()
end

local pending = false
local function schedule()
	if pending then
		return
	end
	pending = true
	task.delay(0.5, function()
		pending = false
		read()
	end)
end
for tag in MapData.LAYERS do
	CollectionService:GetInstanceAddedSignal(tag):Connect(schedule)
	CollectionService:GetInstanceRemovedSignal(tag):Connect(schedule)
end
read()

-- Drawing ----------------------------------------------------------------
local function flatPart(parent: Instance, color: Color3, size: Vector3, cf: CFrame, round: boolean?)
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CastShadow = false
	p.Material = Enum.Material.SmoothPlastic
	p.Color = color
	if round then
		p.Shape = Enum.PartType.Cylinder
		p.Size = Vector3.new(size.Y, size.X, size.X)
		p.CFrame = cf * CFrame.Angles(0, 0, math.pi / 2)
	else
		p.Size = size
		p.CFrame = cf
	end
	p.Parent = parent
	return p
end

-- Roads: every graph edge as a strip with round caps, so crossings, T-joins
-- and corners are connected and rounded.
-- `outline` (optional) draws a darker edge `outlineWidth` studs wide under the road.
function MapData.drawRoads(parent: Instance, color: Color3?, outline: Color3?, outlineWidth: number?)
	local layer = MapData.LAYERS.Road
	local function pass(c: Color3, extra: number, y: number)
		local capW: { [number]: number } = {}
		local degree: { [number]: number } = {}
		for _, e in edges do
			degree[e.a] = (degree[e.a] or 0) + 1
			degree[e.b] = (degree[e.b] or 0) + 1
		end
		-- Skip short stubs that only stick out past a junction (a road part
		-- that's a bit longer than needed), so corners and T-joins look clean.
		local drawn = {}
		for _, e in edges do
			local len = (nodes[e.a] - nodes[e.b]).Magnitude
			local da, db = degree[e.a] or 0, degree[e.b] or 0
			local stub = len <= 24 and ((da == 1 and db >= 3) or (db == 1 and da >= 3))
			if stub then
				degree[e.a] -= 1
				degree[e.b] -= 1
			else
				table.insert(drawn, e)
			end
		end
		for _, e in drawn do
			local w = e.width * layer.Thin + extra * 2
			local p, q = nodes[e.a], nodes[e.b]
			local a, b = Vector3.new(p.X, y, p.Z), Vector3.new(q.X, y, q.Z)
			local len = (b - a).Magnitude
			if len > 0.05 then
				flatPart(parent, c, Vector3.new(w, 0.1, len), CFrame.lookAt((a + b) / 2, b))
			end
			capW[e.a] = math.max(capW[e.a] or 0, w)
			capW[e.b] = math.max(capW[e.b] or 0, w)
		end
		for id, w in capW do
			-- Round joins only where roads meet; dead ends stay square.
			if (degree[id] or 0) < 2 then
				continue
			end
			local p = nodes[id]
			flatPart(parent, c, Vector3.new(w, 0.1, w), CFrame.new(p.X, y, p.Z), true)
		end
	end
	if outline then
		pass(outline, outlineWidth or 1.5, layer.Y)
	end
	pass(color or layer.Color, 0, layer.Y + 0.05)
end

-- Draws all map shapes into `parent` (a Folder inside a WorldModel).
-- `colors` optionally replaces layer colors by name, e.g. { Road = ... },
-- plus RoadEdge for a darker road outline.
function MapData.drawShapes(parent: Instance, colors: { [string]: Color3 }?)
	parent:ClearAllChildren()
	for _, s in shapes do
		local layer = s.layer
		if layer.Name == "Road" then
			continue
		end
		local sx, sz = s.sx, s.sz
		if layer.Thin then
			if sx < sz then
				sx *= layer.Thin
			else
				sz *= layer.Thin
			end
		end
		if layer.Inset then
			sx -= layer.Inset * 2
			sz -= layer.Inset * 2
		end
		local center = Vector3.new(s.pos.X, layer.Y + 0.05, s.pos.Z)
		flatPart(
			parent,
			(colors and colors[layer.Name]) or layer.Color,
			Vector3.new(math.max(sx, 0.2), 0.1, math.max(sz, 0.2)),
			CFrame.lookAt(center, center + s.look)
		)
	end
	MapData.drawRoads(parent, colors and colors.Road, colors and colors.RoadEdge, 1.5)
end

-- Draws a route line (list of points) into `parent`.
function MapData.drawPath(parent: Instance, points: { Vector3 }, width: number)
	parent:ClearAllChildren()
	local y = 0.6
	for i = 1, #points do
		local p = Vector3.new(points[i].X, y, points[i].Z)
		flatPart(parent, MapData.ROUTE, Vector3.new(width, 0.1, width), CFrame.new(p), true)
		if i > 1 then
			local q = Vector3.new(points[i - 1].X, y, points[i - 1].Z)
			local len = (p - q).Magnitude
			if len > 0.05 then
				flatPart(parent, MapData.ROUTE, Vector3.new(width, 0.1, len), CFrame.lookAt((p + q) / 2, p))
			end
		end
	end
end

-- Area covered by the map: centre and size (studs) on the ground.
function MapData.bounds(): (Vector3, Vector3)
	if #shapes == 0 then
		return Vector3.zero, Vector3.new(400, 0, 400)
	end
	local minX, minZ, maxX, maxZ = math.huge, math.huge, -math.huge, -math.huge
	for _, s in shapes do
		local r = math.max(s.sx, s.sz) / 2
		minX, maxX = math.min(minX, s.pos.X - r), math.max(maxX, s.pos.X + r)
		minZ, maxZ = math.min(minZ, s.pos.Z - r), math.max(maxZ, s.pos.Z + r)
	end
	return Vector3.new((minX + maxX) / 2, 0, (minZ + maxZ) / 2), Vector3.new(maxX - minX, 0, maxZ - minZ)
end

-- Routing ----------------------------------------------------------------
local function nearestSeg(p: Vector3): (Seg?, number, Vector3)
	local best, bestT, bestQ, bestD = nil, 0, p, math.huge
	for _, s in segs do
		local t, q = closestOn(s, p)
		local d = (q - p).Magnitude
		if d < bestD then
			best, bestT, bestQ, bestD = s, t, q, d
		end
	end
	return best, bestT, bestQ
end

-- Shortest way along the roads from `from` to `to`. Returns ground points,
-- starting at `from` and ending at `to`.
function MapData.route(from: Vector3, to: Vector3): { Vector3 }
	from = Vector3.new(from.X, 0, from.Z)
	to = Vector3.new(to.X, 0, to.Z)
	local sSeg, sT, sQ = nearestSeg(from)
	local eSeg, eT, eQ = nearestSeg(to)
	if not sSeg or not eSeg then
		return { from, to }
	end

	-- Temporary nodes for the start (-1) and end (-2) on their roads.
	local pos = { [-1] = sQ, [-2] = eQ }
	local extra: { [number]: { [number]: number } } = { [-1] = {}, [-2] = {} }
	local function tempLink(a: number, b: number)
		local pa, pb = pos[a] or nodes[a], pos[b] or nodes[b]
		local d = (pa - pb).Magnitude
		extra[a] = extra[a] or {}
		extra[b] = extra[b] or {}
		extra[a][b] = d
		extra[b][a] = d
	end
	local function attach(id: number, s: Seg, t: number)
		local prev, nxt
		for _, e in s.entries do
			if e.t <= t then
				prev = e
			elseif not nxt then
				nxt = e
			end
		end
		if prev then
			tempLink(id, prev.id)
		end
		if nxt then
			tempLink(id, nxt.id)
		end
	end
	attach(-1, sSeg, sT)
	attach(-2, eSeg, eT)
	if sSeg == eSeg then
		tempLink(-1, -2)
	end

	-- Dijkstra (graph is small).
	local dist: { [number]: number } = { [-1] = 0 }
	local prevOf: { [number]: number } = {}
	local done: { [number]: boolean } = {}
	while true do
		local cur, curD = nil, math.huge
		for id, d in dist do
			if not done[id] and d < curD then
				cur, curD = id, d
			end
		end
		if cur == nil or cur == -2 then
			break
		end
		done[cur] = true
		local function relax(nb: number, w: number)
			local nd = curD + w
			if nd < (dist[nb] or math.huge) then
				dist[nb] = nd
				prevOf[nb] = cur
			end
		end
		for nb, w in (cur > 0 and adj[cur]) or {} do
			relax(nb, w)
		end
		for nb, w in extra[cur] or {} do
			relax(nb, w)
		end
	end

	if not dist[-2] then
		return { from, to }
	end
	local path = { to, eQ }
	local id = prevOf[-2]
	while id and id ~= -1 do
		table.insert(path, nodes[id])
		id = prevOf[id]
	end
	table.insert(path, sQ)
	table.insert(path, from)
	-- Reverse to start at `from`.
	local out = {}
	for i = #path, 1, -1 do
		table.insert(out, path[i])
	end
	return out
end

return MapData
