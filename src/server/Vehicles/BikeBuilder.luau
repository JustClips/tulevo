--[[
	Builds a motorbike (Def.Kind == "Bike") for Vehicles/Builder. Same idea as the cars, two wheels:

		Model (tag "Vehicle", attributes VehicleId, Bike)
		  Chassis          PrimaryPart, invisible collision box, carries the physics
		    WheelF / WheelR      Attachments: suspension tops
		    ForceF / ForceR      Attachments with a VectorForce (at the centre of mass height)
		    Upright              Attachment (X axis = chassis up) + AlignOrientation that keeps it upright
		    DoorPrompt           Attachment with the "Ride" ProximityPrompt, on the left
		  Ballast          heavy invisible slab low in the bike
		  BodyRoot         on a Weld "Lean" to Chassis (the client leans the whole bike into turns)
		    DriverSeat       VehicleSeat on BodyRoot, so the rider leans with the bike
		    SteerRoot / ForkRoot / FrontHub / SwingRoot / RearHub / StandRoot
		                     invisible hinge parts (Shared/Vehicles/BikeRig), each on a Weld the client
		                     turns: Steer, Fork (slides), Spin, Swing, Spin, Stand
		  Body             every mesh, welded to BodyRoot or to its group's hinge part

	The meshes come from Def.Model (Shared.ModelIds), painted from Shared.ModelLooks and
	Shared.TextureIds like the Showcase. Until the model loads it gets a block placeholder.
]]

local CollectionService = game:GetService("CollectionService")
local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Vehicles = require(Shared:WaitForChild("Vehicles"))
local BikeRig = require(Shared:WaitForChild("Vehicles"):WaitForChild("BikeRig"))
local ModelIds = require(Shared:WaitForChild("ModelIds"))
local ModelLooks = require(Shared:WaitForChild("ModelLooks"))
local TextureIds = require(Shared:WaitForChild("TextureIds"))

local BikeBuilder = {}

local HULL_DENSITY = 0.1
local BALLAST_DENSITY = 8

local function part(props): BasePart
	local className = props.ClassName or "Part"
	props.ClassName = nil
	local p = Instance.new(className) :: BasePart
	p.Anchored = false
	p.CanCollide = false
	p.CanTouch = false
	p.CanQuery = false
	p.Massless = true
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.Material = Enum.Material.SmoothPlastic
	for k, v in props do
		(p :: any)[k] = v
	end
	return p
end

-- part1 = part0 * c0 (rest pose); the client changes C0 to move it
local function weld(name: string, part0: BasePart, part1: BasePart, c0: CFrame): Weld
	local w = Instance.new("Weld")
	w.Name = name
	w.Part0 = part0
	w.Part1 = part1
	w.C0 = c0
	w.Parent = part1
	return w
end

local templates: { [string]: Model | false } = {}

local function template(name: string): Model?
	if templates[name] == nil then
		templates[name] = false
		local id = ModelIds[name]
		if not id then
			warn(`[Vehicles] no model id for {name} yet (tools/upload_models.py); using the placeholder`)
		else
			local ok, container = pcall(InsertService.LoadAsset, InsertService, id)
			if ok then
				local m = Instance.new("Model")
				m.Name = name
				for _, child in container:GetChildren() do
					child.Parent = m
				end
				container:Destroy()
				templates[name] = m
			else
				warn(`[Vehicles] could not load model {name} ({id}): {container}`)
			end
		end
	end
	return templates[name] or nil
end

-- The uploaded meshes, keyed by part name, each with its rest CFrame in chassis space.
-- Where the importer put the bike is measured from the tyres (hub centred) and the front brake
-- rotors (left/right pair), so any import axes or units work.
local function meshes(def): ({ [string]: { Part: MeshPart, Rest: CFrame } }?, Model?)
	local src = template(def.Model)
	if not src then
		return nil
	end
	src = src:Clone()
	local parts: { [string]: MeshPart } = {}
	for _, d in src:GetDescendants() do
		if d:IsA("MeshPart") then
			parts[d.Name] = d
		end
	end
	local front, rear, rotL, rotR = parts.FrontTyre, parts.RearTyre, parts.FrontRotorL, parts.FrontRotorR
	if not (front and rear and rotL and rotR) then
		warn(
			`[Vehicles] {def.Model} is missing FrontTyre / RearTyre / FrontRotorL / FrontRotorR; using the placeholder`
		)
		src:Destroy()
		return nil
	end
	local pts = BikeRig.points(def)

	-- import space frame on the hubs, and the same frame in chassis space
	local function frameOf(f: Vector3, r: Vector3, right: Vector3): CFrame
		local fwd = (f - r).Unit
		right = (right - fwd * right:Dot(fwd)).Unit
		local up = right:Cross(fwd)
		return CFrame.fromMatrix((f + r) / 2, right, up, -fwd)
	end
	local imported = frameOf(front.Position, rear.Position, rotR.Position - rotL.Position)
	local chassisFrame = frameOf(pts.FrontAxle, pts.RearAxle, Vector3.xAxis)
	local k = (pts.FrontAxle - pts.RearAxle).Magnitude / (front.Position - rear.Position).Magnitude -- import units -> studs

	local out = {}
	for name, p in parts do
		local rel = imported:ToObjectSpace(p.CFrame)
		p.Size *= k
		out[name] = { Part = p, Rest = chassisFrame * (CFrame.new(rel.Position * k) * rel.Rotation) }
	end
	return out, src
end

local function paint(def, p: MeshPart)
	local looks = ModelLooks[def.Model]
	local look = looks and (looks[p.Name] or looks[(string.gsub(p.Name, "[LR]$", ""))])
	if look then
		p.Color = look.Color
		p.Material = look.Material
		p.Reflectance = look.Reflectance or 0
		p.Transparency = look.Transparency or 0
	end
	local textures = TextureIds[def.Model]
	if textures and textures[p.Name] then
		p.TextureID = `rbxassetid://{textures[p.Name]}`
	end
	p.CastShadow = (look and look.Transparency or 0) < 0.3
end

-- Simple stand-in until the model is uploaded / loads: a body block and two wheels.
local function placeholder(def, pts, roots, folder: Folder)
	local s = def.Rig.Scale
	local function add(name, root: BasePart, rootRest: CFrame, props)
		props.Name = name
		local p = part(props)
		p.Parent = folder
		weld("Weld", root, p, rootRest:Inverse() * props.CFrame)
	end
	local white, dark = Color3.fromRGB(225, 226, 230), Color3.fromRGB(28, 28, 32)
	add("Body", roots.Body.Part, roots.Body.Rest, {
		Size = Vector3.new(0.34 * s, 0.38 * s, 1.1 * s),
		CFrame = CFrame.new(0, def.Rig.Ground + 0.68 * s, -0.05 * s),
		Color = white,
	})
	add("Seat", roots.Body.Part, roots.Body.Rest, {
		Size = Vector3.new(0.26 * s, 0.06 * s, 0.45 * s),
		CFrame = CFrame.new(pts.Seat + Vector3.new(0, 0.03 * s, 0)),
		Color = dark,
	})
	for _, w in
		{ { "FrontWheel", pts.FrontAxle, def.Wheels.Radius }, { "RearWheel", pts.RearAxle, def.Wheels.RearRadius } }
	do
		local root = roots[w[1]]
		add(w[1], root.Part, root.Rest, {
			Shape = Enum.PartType.Cylinder,
			Size = Vector3.new(0.18 * s, w[3] * 2, w[3] * 2),
			CFrame = CFrame.new(w[2]),
			Color = dark,
		})
	end
end

function BikeBuilder.build(def): Model
	local model = Instance.new("Model")
	model.Name = def.Name
	model:SetAttribute("VehicleId", def.Id)
	model:SetAttribute("Bike", true)
	local s = def.Size
	local pts = BikeRig.points(def)

	local chassis = part({
		Name = "Chassis",
		Size = s,
		CFrame = CFrame.new(),
		Transparency = 1,
		CanCollide = true,
		CanQuery = true, -- bullets hit bikes
		Massless = false,
		CustomPhysicalProperties = PhysicalProperties.new(HULL_DENSITY, 0.3, 0, 1, 1),
	})
	chassis.Parent = model
	model.PrimaryPart = chassis

	local ballastSize = Vector3.new(s.X * 0.6, 0.4, s.Z * 0.7)
	local ballastY = -s.Y / 2 + 0.2
	local ballast = part({
		Name = "Ballast",
		Size = ballastSize,
		CFrame = CFrame.new(0, ballastY, 0),
		Transparency = 1,
		Massless = false,
		CustomPhysicalProperties = PhysicalProperties.new(BALLAST_DENSITY, 0.3, 0, 1, 1),
	})
	ballast.Parent = model
	local wc = Instance.new("WeldConstraint")
	wc.Part0 = chassis
	wc.Part1 = ballast
	wc.Parent = ballast

	local mHull = s.X * s.Y * s.Z * HULL_DENSITY
	local mBallast = ballastSize.X * ballastSize.Y * ballastSize.Z * BALLAST_DENSITY
	local comY = (mBallast * ballastY) / (mHull + mBallast)

	for _, name in { "F", "R" } do
		local mountPos = def.Wheels[name]
		local a = Instance.new("Attachment")
		a.Name = `Wheel{name}`
		a.Position = mountPos
		a.Parent = chassis
		-- grip pushes at the centre of mass height, so turning doesn't try to tip the bike over
		local f = Instance.new("Attachment")
		f.Name = `Force{name}`
		f.Position = Vector3.new(0, comY, mountPos.Z)
		f.Parent = chassis
		local vf = Instance.new("VectorForce")
		vf.Attachment0 = f
		vf.RelativeTo = Enum.ActuatorRelativeTo.World
		vf.ApplyAtCenterOfMass = false
		vf.Force = Vector3.zero
		vf.Parent = f
	end

	-- keeps the chassis' up on the ground's up (BikePhysics sets PrimaryAxis); yaw stays free
	local upright = Instance.new("Attachment")
	upright.Name = "Upright"
	upright.CFrame = CFrame.fromMatrix(Vector3.zero, Vector3.yAxis, Vector3.zAxis) -- X axis = chassis up
	upright.Parent = chassis
	local align = Instance.new("AlignOrientation")
	align.Mode = Enum.OrientationAlignmentMode.OneAttachment
	align.AlignType = Enum.AlignType.PrimaryAxisParallel
	align.Attachment0 = upright
	align.PrimaryAxis = Vector3.yAxis
	align.MaxTorque = (mHull + mBallast) * 6000
	align.MaxAngularVelocity = 20
	align.Responsiveness = 40
	align.Parent = upright

	-- body root (leans) and the hinge parts
	local bodyRoot = part({ Name = "BodyRoot", Size = Vector3.new(1, 1, 1), CFrame = chassis.CFrame, Transparency = 1 })
	bodyRoot.Parent = model
	weld("Lean", chassis, bodyRoot, CFrame.new())
	local roots = { Body = { Part = bodyRoot, Rest = CFrame.new() } }
	local function root(name: string, weldName: string, parent: string, at: Vector3)
		local p = part({ Name = name, Size = Vector3.new(0.2, 0.2, 0.2), Transparency = 1 })
		local parentRest = roots[parent].Rest
		weld(weldName, roots[parent].Part, p, parentRest:Inverse() * CFrame.new(at))
		p.Parent = model
		return { Part = p, Rest = CFrame.new(at) }
	end
	roots.Steer = root("SteerRoot", "Steer", "Body", pts.Hinge)
	roots.Fork = root("ForkRoot", "Fork", "Steer", pts.Hinge)
	roots.FrontWheel = root("FrontHub", "Spin", "Fork", pts.FrontAxle)
	roots.Swing = root("SwingRoot", "Swing", "Body", pts.SwingPivot)
	roots.RearWheel = root("RearHub", "Spin", "Swing", pts.RearAxle)
	roots.Stand = root("StandRoot", "Stand", "Body", pts.StandPivot)

	local seat = part({
		ClassName = "VehicleSeat",
		Name = "DriverSeat",
		Size = Vector3.new(1.4, 0.2, 1.4),
		Transparency = 1,
	}) :: VehicleSeat
	seat.MaxSpeed = 0
	seat.Torque = 0
	seat.TurnSpeed = 0
	seat.HeadsUpDisplay = false
	weld("Weld", bodyRoot, seat, CFrame.new(def.DriverSeat - Vector3.new(0, seat.Size.Y / 2, 0)))
	seat.Parent = model

	local door = Instance.new("Attachment")
	door.Name = "DoorPrompt"
	door.Position = Vector3.new(def.ExitSide * (s.X / 2 + 0.5), 0.5, def.DriverSeat.Z)
	door.Parent = chassis
	local prompt = Instance.new("ProximityPrompt")
	prompt.Name = "Drive"
	prompt.ActionText = "Ride"
	prompt.ObjectText = def.Name
	prompt.KeyboardKeyCode = Enum.KeyCode.F
	prompt.GamepadKeyCode = Enum.KeyCode.ButtonY
	prompt.HoldDuration = 0
	prompt.MaxActivationDistance = Config.Vehicles.EnterDistance
	prompt.RequiresLineOfSight = false
	prompt.Parent = door

	local bodyFolder = Instance.new("Folder")
	bodyFolder.Name = "Body"
	bodyFolder.Parent = model

	local parts, src = meshes(def)
	if parts then
		local groupOf = BikeRig.groupOf(def)
		for name, m in parts do
			local p = m.Part
			p.Anchored = false
			p.CanCollide = false
			p.CanTouch = false
			p.CanQuery = false
			p.Massless = true
			paint(def, p)
			local r = roots[groupOf[name] or "Body"]
			p.CFrame = chassis.CFrame * m.Rest
			weld("Weld", r.Part, p, r.Rest:Inverse() * m.Rest)
			p.Parent = bodyFolder
		end
		if src then
			src:Destroy()
		end
	else
		placeholder(def, pts, roots, bodyFolder)
	end

	CollectionService:AddTag(model, Vehicles.TAG)
	return model
end

return BikeBuilder
