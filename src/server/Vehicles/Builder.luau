--[[
	Builds a vehicle model from its Def. Until a car has a real mesh (Def.Model), it gets a
	simple block placeholder in its colours. Either way the model has the same layout, which
	is all the driving code needs:

		Model (tag "Vehicle", attribute VehicleId)
		  Chassis          PrimaryPart, invisible collision box, carries the physics
		    Wheel<FL|FR|RL|RR>   Attachments: top of each suspension
		    Force<FL|...>        Attachments with a VectorForce, where wheel forces push
		    DoorPrompt           Attachment with the "Drive" ProximityPrompt
		  Ballast          heavy invisible slab low in the car (keeps it from rolling over)
		  DriverSeat       VehicleSeat
		  Wheel_<FL|...>   wheel visuals, welded to Chassis by a Weld named "Mount" (the client
		                   moves them up/down, steers and spins them)
		  Body             visual parts (massless, no collision)

	Motorbikes (Def.Kind == "Bike") are built by Vehicles/BikeBuilder instead.

	Cars with a real model (Def.Model + Def.Rig) instead get, from the uploaded mesh:
		  Wheels/Wheel_<FL|...>, Wheels/Caliper_<FL|...>   "Mount" welds as above
		  BodyRoot         invisible part on a Weld "Lean" to Chassis (the client tilts it)
		    every other mesh welded to BodyRoot; SteeringWheel / Pedal_Gas / Pedal_Brake
		    on Welds named "Rig" whose C0 sits on the hinge (the client turns them)
]]

local CollectionService = game:GetService("CollectionService")
local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Vehicles = require(Shared:WaitForChild("Vehicles"))
local ModelIds = require(Shared:WaitForChild("ModelIds"))

local Builder = {}

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

local function weld(a: BasePart, b: BasePart)
	local w = Instance.new("WeldConstraint")
	w.Part0 = a
	w.Part1 = b
	w.Parent = b
end

-- Placeholder sedan-ish body from blocks. Positions are around the Chassis centre.
local function placeholderBody(def, chassis: BasePart, folder: Folder)
	local s = def.Size
	local body, trim = def.Colors.Body, def.Colors.Trim
	local topY = s.Y / 2
	local bodyW = s.X - 0.8 -- narrower than the hull so the wheels show
	local cabinZ = def.DriverSeat.Z + 0.4

	local function add(name, props)
		props.Name = name
		local p = part(props)
		p.Parent = folder
		weld(chassis, p)
		return p
	end

	add("Lower", { Size = Vector3.new(bodyW, s.Y, s.Z), CFrame = CFrame.new(0, 0, 0), Color = body })
	add("Hood", { Size = Vector3.new(bodyW - 0.2, 0.3, 4.2), CFrame = CFrame.new(0, topY + 0.15, -s.Z / 2 + 2.2), Color = body })
	add("Trunk", { Size = Vector3.new(bodyW - 0.2, 0.3, 2.2), CFrame = CFrame.new(0, topY + 0.15, s.Z / 2 - 1.2), Color = body })

	-- cabin: glass box + sloped windscreen + sloped rear window + roof
	local glass = Color3.fromRGB(40, 50, 60)
	local cabinLen, cabinH = 4.6, 2.5
	add("Glass", {
		Size = Vector3.new(bodyW - 0.6, cabinH, cabinLen),
		CFrame = CFrame.new(0, topY + cabinH / 2, cabinZ),
		Color = glass,
		Material = Enum.Material.Glass,
		Transparency = 0.45,
	})
	add("Windscreen", {
		ClassName = "WedgePart",
		Size = Vector3.new(bodyW - 0.6, cabinH, 2),
		CFrame = CFrame.new(0, topY + cabinH / 2, cabinZ - cabinLen / 2 - 1),
		Color = glass,
		Material = Enum.Material.Glass,
		Transparency = 0.45,
	})
	add("RearWindow", {
		ClassName = "WedgePart",
		Size = Vector3.new(bodyW - 0.6, cabinH, 1.4),
		CFrame = CFrame.new(0, topY + cabinH / 2, cabinZ + cabinLen / 2 + 0.7) * CFrame.Angles(0, math.pi, 0),
		Color = glass,
		Material = Enum.Material.Glass,
		Transparency = 0.45,
	})
	add("Roof", { Size = Vector3.new(bodyW - 0.5, 0.25, cabinLen + 0.2), CFrame = CFrame.new(0, topY + cabinH + 0.12, cabinZ), Color = body })

	-- trim and lights
	add("BumperFront", { Size = Vector3.new(bodyW + 0.1, 0.6, 0.4), CFrame = CFrame.new(0, -s.Y / 2 + 0.3, -s.Z / 2 - 0.1), Color = trim })
	add("BumperRear", { Size = Vector3.new(bodyW + 0.1, 0.6, 0.4), CFrame = CFrame.new(0, -s.Y / 2 + 0.3, s.Z / 2 + 0.1), Color = trim })
	add("Grille", { Size = Vector3.new(2.6, 0.5, 0.1), CFrame = CFrame.new(0, 0.25, -s.Z / 2 - 0.03), Color = trim })
	for _, side in { -1, 1 } do
		add("Headlight", {
			Size = Vector3.new(1.3, 0.45, 0.1),
			CFrame = CFrame.new(side * (bodyW / 2 - 0.9), 0.3, -s.Z / 2 - 0.04),
			Color = Color3.fromRGB(255, 244, 214),
			Material = Enum.Material.Neon,
		})
		add("Taillight", {
			Size = Vector3.new(1.2, 0.4, 0.1),
			CFrame = CFrame.new(side * (bodyW / 2 - 0.8), 0.35, s.Z / 2 + 0.04),
			Color = Color3.fromRGB(200, 20, 20),
			Material = Enum.Material.Neon,
		})
		add("Skirt", { Size = Vector3.new(0.12, 0.35, s.Z - 6.5), CFrame = CFrame.new(side * (bodyW / 2 + 0.03), -s.Y / 2 + 0.25, 0), Color = trim })
	end
end

local function wheel(def, chassis: BasePart, name: string, folder: Model)
	local r, width = def.Wheels.Radius, def.Wheels.Width
	local mount = def.Wheels[name]
	local rest = def.Suspension.Length * 0.5
	local hub = CFrame.new(mount - Vector3.new(0, rest, 0))

	local tire = part({
		Name = `Wheel_{name}`,
		Shape = Enum.PartType.Cylinder, -- axle along X
		Size = Vector3.new(width, r * 2, r * 2),
		CFrame = hub,
		Color = Color3.fromRGB(25, 25, 25),
	})
	local rim = part({
		Name = "Rim",
		Shape = Enum.PartType.Cylinder,
		Size = Vector3.new(width + 0.04, r * 1.2, r * 1.2),
		CFrame = hub,
		Color = Color3.fromRGB(170, 172, 178),
		Material = Enum.Material.Metal,
	})
	local spoke = part({
		Name = "Spoke",
		Size = Vector3.new(width + 0.08, 0.3, r * 1.15),
		CFrame = hub,
		Color = Color3.fromRGB(110, 112, 118),
		Material = Enum.Material.Metal,
	})
	rim.Parent = tire
	spoke.Parent = tire
	weld(tire, rim)
	weld(tire, spoke)

	local m = Instance.new("Weld")
	m.Name = "Mount"
	m.Part0 = chassis
	m.Part1 = tire
	m.C0 = hub
	m.Parent = tire
	tire.Parent = folder
end

-- ------------------------------------------------------------------ real models

local templates: { [string]: Model | false } = {}

-- The uploaded model for a Def (loaded once, then cloned), or nil.
local function template(def): Model?
	local name = def.Model
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

-- Blender meters (X = car's left, Y = back, Z = up) -> chassis space studs.
local function toCar(rig, v: Vector3): Vector3
	return Vector3.new(-v.X, v.Z, v.Y) * rig.Scale + Vector3.new(0, rig.Ground, 0)
end

local function hingeWeld(name: string, part0: BasePart, part1: BasePart, hinge: Vector3, rest: CFrame)
	-- part1 = part0 * C0 * C1^-1; C0 on the hinge, so turning C0 turns the part around it
	local w = Instance.new("Weld")
	w.Name = name
	w.Part0 = part0
	w.Part1 = part1
	w.C0 = CFrame.new(hinge)
	w.C1 = rest:Inverse() * CFrame.new(hinge)
	w.Parent = part1
	return w
end

-- Puts the uploaded meshes on the car. Returns false (nothing changed) if the model is unusable.
local function realBody(def, chassis: BasePart, model: Model): boolean
	local rig = def.Rig
	local src = template(def)
	if not rig or not src then
		return false
	end
	src = src:Clone()
	local parts: { [string]: BasePart } = {}
	for _, d in src:GetDescendants() do
		if d:IsA("BasePart") then
			parts[d.Name] = d
		end
	end
	local w = {}
	for _, name in Vehicles.WHEELS do
		w[name] = parts[`Wheel_{name}`]
		if not w[name] then
			warn(`[Vehicles] {def.Model} has no Wheel_{name}; using the placeholder`)
			src:Destroy()
			return false
		end
	end

	-- Where the importer put the car: measure it from the wheel centres (works whatever axes
	-- or units the import used). The wheels' middle is Blender (0, 0, HubHeight).
	local front = (w.FL.Position + w.FR.Position) / 2
	local rear = (w.RL.Position + w.RR.Position) / 2
	local fwd = (front - rear).Unit
	local right = w.FR.Position - w.FL.Position
	right = (right - fwd * right:Dot(fwd)).Unit
	local up = (-fwd):Cross(right)
	local frame = CFrame.fromMatrix((front + rear) / 2, right, up, -fwd)
	local k = rig.Wheelbase * rig.Scale / (front - rear).Magnitude -- import units -> studs
	local middle = toCar(rig, Vector3.new(0, 0, rig.HubHeight))

	local bodyRoot = part({
		Name = "BodyRoot",
		Size = Vector3.new(1, 1, 1),
		CFrame = chassis.CFrame,
		Transparency = 1,
	})
	bodyRoot.Parent = model
	local lean = Instance.new("Weld")
	lean.Name = "Lean"
	lean.Part0 = chassis
	lean.Part1 = bodyRoot
	lean.Parent = bodyRoot

	local wheels = Instance.new("Model")
	wheels.Name = "Wheels"
	wheels.Parent = model
	local bodyFolder = Instance.new("Folder")
	bodyFolder.Name = "Body"
	bodyFolder.Parent = model

	-- tinted glass (windscreen) and clear glass (headlamp covers)
	local glass = {}
	for _, n in rig.Glass or {} do
		glass[n] = { Transparency = 0.55, Color = Color3.fromRGB(30, 38, 44) }
	end
	for _, n in rig.ClearGlass or {} do
		glass[n] = { Transparency = 0.8, Color = Color3.fromRGB(225, 232, 240) }
	end
	local moving = {}
	if rig.SteeringWheel then
		moving[rig.SteeringWheel.Part] = rig.SteeringWheel.Center
	end
	for _, p in (rig.Pedals or {}) :: any do
		if type(p) == "table" then
			moving[p.Part] = p.Pivot
		end
	end

	local restOf: { [BasePart]: CFrame } = {}
	local pieces = {}
	for name, p in parts do
		local rel = frame:ToObjectSpace(p.CFrame)
		local rest = CFrame.new(middle + rel.Position * k) * rel.Rotation -- chassis space
		p.Size *= k
		p.Anchored = false
		p.CanCollide = false
		p.CanTouch = false
		p.CanQuery = false
		p.Massless = true
		p.CastShadow = not glass[name]
		p.CFrame = chassis.CFrame * rest
		if glass[name] then
			p.Transparency = glass[name].Transparency
			p.Material = Enum.Material.Glass
			p.Color = glass[name].Color
			for _, d in p:GetChildren() do
				if d:IsA("SurfaceAppearance") then
					d:Destroy()
				end
			end
		end

		-- "<Part>__<Texture>" pieces (tiling carbon, leather, alu... textures) ride on their part
		local base = name:match("^(.-)__")
		local wheel = name:match("^Wheel_(%u%u)$") or name:match("^Caliper_(%u%u)$")
		if base and parts[base] then
			restOf[p] = rest
			table.insert(pieces, { Part = p, Base = parts[base] })
		elseif wheel then
			-- hinge on the model's hub, straight under the suspension top; Vehicles/Wheels
			-- then moves C0 with the suspension, steering and (wheels only) spin
			local mount = def.Wheels[wheel]
			local hub = Vector3.new(mount.X, rig.Ground + rig.HubHeight * rig.Scale, mount.Z)
			hingeWeld("Mount", chassis, p, hub, rest)
			p.Parent = wheels
		elseif moving[name] then
			hingeWeld("Rig", bodyRoot, p, toCar(rig, moving[name]), rest)
			p.Parent = bodyFolder
		else
			hingeWeld("Weld", bodyRoot, p, rest.Position, rest)
			p.Parent = bodyFolder
		end
		restOf[p] = rest
	end
	for _, piece in pieces do
		local w = Instance.new("Weld")
		w.Name = "Piece"
		w.Part0 = piece.Base
		w.Part1 = piece.Part
		w.C0 = restOf[piece.Base]:Inverse() * restOf[piece.Part]
		w.Parent = piece.Part
		piece.Part.Parent = piece.Base.Parent
	end
	src:Destroy()
	model:SetAttribute("RealModel", true)
	return true
end

function Builder.build(def): Model
	if def.Kind == "Bike" then
		return require(script.Parent:WaitForChild("BikeBuilder")).build(def)
	end
	local model = Instance.new("Model")
	model.Name = def.Name
	model:SetAttribute("VehicleId", def.Id)
	local s = def.Size

	local chassis = part({
		Name = "Chassis",
		Size = s,
		CFrame = CFrame.new(),
		Transparency = 1,
		CanCollide = true,
		CanQuery = true, -- bullets hit cars
		Massless = false,
		CustomPhysicalProperties = PhysicalProperties.new(HULL_DENSITY, 0.3, 0, 1, 1),
	})
	chassis.Parent = model
	model.PrimaryPart = chassis

	local ballastSize = Vector3.new(s.X - 1.5, 0.4, s.Z - 4)
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
	weld(chassis, ballast)

	-- centre of mass height (hull + ballast), for where wheel forces push
	local mHull = s.X * s.Y * s.Z * HULL_DENSITY
	local mBallast = ballastSize.X * ballastSize.Y * ballastSize.Z * BALLAST_DENSITY
	local comY = (mBallast * ballastY) / (mHull + mBallast)

	for _, name in Vehicles.WHEELS do
		local mountPos = def.Wheels[name]
		local a = Instance.new("Attachment")
		a.Name = `Wheel{name}`
		a.Position = mountPos
		a.Parent = chassis

		-- pushing a little below the centre of mass gives a small natural lean out of turns
		local f = Instance.new("Attachment")
		f.Name = `Force{name}`
		f.Position = Vector3.new(mountPos.X, comY - 0.3, mountPos.Z)
		f.Parent = chassis
		local vf = Instance.new("VectorForce")
		vf.Attachment0 = f
		vf.RelativeTo = Enum.ActuatorRelativeTo.World
		vf.ApplyAtCenterOfMass = false
		vf.Force = Vector3.zero
		vf.Parent = f
	end

	local seat = part({
		ClassName = "VehicleSeat",
		Name = "DriverSeat",
		Size = Vector3.new(2, 0.4, 2),
		CFrame = CFrame.new(def.DriverSeat),
		Transparency = 1,
	}) :: VehicleSeat
	seat.MaxSpeed = 0 -- our own physics drives the car, not the seat
	seat.Torque = 0
	seat.TurnSpeed = 0
	seat.HeadsUpDisplay = false
	seat.Parent = model
	weld(chassis, seat)

	local door = Instance.new("Attachment")
	door.Name = "DoorPrompt"
	door.Position = Vector3.new(def.ExitSide * (s.X / 2 + 0.3), 0.6, def.DriverSeat.Z)
	door.Parent = chassis
	local prompt = Instance.new("ProximityPrompt")
	prompt.Name = "Drive"
	prompt.ActionText = "Drive"
	prompt.ObjectText = def.Name
	prompt.KeyboardKeyCode = Enum.KeyCode.F
	prompt.GamepadKeyCode = Enum.KeyCode.ButtonY
	prompt.HoldDuration = 0
	prompt.MaxActivationDistance = Config.Vehicles.EnterDistance
	prompt.RequiresLineOfSight = false
	prompt.Parent = door

	if not (def.Model and realBody(def, chassis, model)) then
		local wheels = Instance.new("Model")
		wheels.Name = "Wheels"
		wheels.Parent = model
		for _, name in Vehicles.WHEELS do
			wheel(def, chassis, name, wheels)
		end

		local bodyFolder = Instance.new("Folder")
		bodyFolder.Name = "Body"
		bodyFolder.Parent = model
		placeholderBody(def, chassis, bodyFolder)
	end

	CollectionService:AddTag(model, Vehicles.TAG)
	return model
end

return Builder
