--[[
	Puts everyone aiming a gun into the rifle stance and locks their chest to the aim, on top
	of the animations.

	Stance (GTA): the whole body is bladed, not just the chest. The hips, and the legs with
	them, turn Config.Weapons.AimStance degrees right of the aim (less while moving), so the
	waist only twists the last few degrees. The root part still faces the aim, so the server's
	aim checks and the movement code don't change; Weapons/init picks the side-step blend
	relative to the turned hips (State.HipTurn).

	Planted feet: aiming while standing still, the feet stay where they are as the body turns
	(the hips are counter-turned). Once the body is AimStep.Turn degrees away from the feet,
	or the aim settles more than AimStep.Settle away, a turn step plays (Tulevo_TurnStepLeft /
	Right, art/anim/steps.py) and the feet catch up. Other players: GunPlant (from the Pose
	remote) says whether their feet are planted, and their step clips (replicated) say when.

	The Aim clip (art/anim/gun.py) shoulders the rifle with the chest bladed (AIM_UT below),
	but the chest hangs off the hips, and the walk/strafe clips bob, sway and turn the hips,
	so on its own the rifle would wobble with every step. Every frame, right after the
	animations are applied (PreSimulation), this sets the Waist joint so the UpperTorso has
	exactly the aim orientation in the world: facing yaw + aim pitch (up/down) + the blade.
	Arms, head and gun hang off the chest, so they're locked too.

	Lean (hold Q / E, gun or not): after all that the body leans over: the hips tip a little
	(legs kept upright, feet stay put), the chest tilts the rest of Config.Weapons.LeanAngle
	round the aim direction (so the barrel still points at the crosshair) and the head tilts
	back a bit toward level, like peeking round a corner.

	Local player: values from Weapons/State (AimBlend = how much of the Aim pose is in,
	Pitch, FeetPlant, Lean). Other players: character attributes GunUp / GunPitch / GunPlant /
	GunLean (server copies them from the Pose remote), smoothed here.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local AnimIds = require(Shared:WaitForChild("AnimIds"))

local State = require(script.Parent:WaitForChild("State"))

local GunPose = {}

-- UpperTorso pose of Weapon_Rifle_Aim relative to an upright body (gun.py AIM_TORSO)
local AIM_UT = CFrame.Angles(0, math.rad(-48), 0) * CFrame.Angles(math.rad(-4), 0, 0)

local STEP_TIME = 0.42 -- Tulevo_TurnStep length (art/anim/steps.py TURN_TIME)
local MAX_LAG = math.rad(75) -- feet never trail the body further than this (they slide)
local STEP_IDS = {
	[(AnimIds :: any).Tulevo_TurnStepLeft or "-"] = true,
	[(AnimIds :: any).Tulevo_TurnStepRight or "-"] = true,
}

type Rig = {
	root: BasePart,
	lowerRoot: Motor6D,
	waist: Motor6D,
	neck: Motor6D?,
	hips: { Motor6D },
	humanoid: Humanoid?,
	blend: number,
	pitch: number,
	turn: number, -- smoothed hip turn (radians right of the aim)
	feetYaw: number?, -- world yaw the planted feet face
	lastYaw: number,
	still: number, -- seconds the body hasn't been turning
	stepUntil: number, -- os.clock() until the current turn step ends
	steps: { [number]: AnimationTrack }?, -- local player: -1 left, 1 right
	lean: number, -- other players: smoothed GunLean (-1..1)
}
local rigs: { [Model]: Rig } = {}

local function rigOf(character: Model): Rig?
	local r = rigs[character]
	if r and r.waist.Parent and r.lowerRoot.Parent then
		return r
	end
	local root = character:FindFirstChild("HumanoidRootPart")
	local lt = character:FindFirstChild("LowerTorso")
	local ut = character:FindFirstChild("UpperTorso")
	local lowerRoot = lt and lt:FindFirstChild("Root")
	local waist = ut and ut:FindFirstChild("Waist")
	if not (root and root:IsA("BasePart") and lowerRoot and lowerRoot:IsA("Motor6D") and waist and waist:IsA("Motor6D")) then
		return nil
	end
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	local function motorIn(partName: string, name: string): Motor6D?
		local part = character:FindFirstChild(partName)
		local m = part and part:FindFirstChild(name)
		return if m and m:IsA("Motor6D") then m else nil
	end
	local hips = {}
	for _, h in { motorIn("RightUpperLeg", "RightHip"), motorIn("LeftUpperLeg", "LeftHip") } do
		table.insert(hips, h)
	end
	local rig: Rig = {
		root = root,
		lowerRoot = lowerRoot,
		waist = waist,
		neck = motorIn("Head", "Neck"),
		hips = hips,
		humanoid = humanoid,
		blend = 0,
		pitch = 0,
		turn = 0,
		feetYaw = nil,
		lastYaw = 0,
		still = 0,
		stepUntil = 0,
		steps = nil,
		lean = 0,
	}
	rigs[character] = rig
	-- a turn step starting (ours or replicated from its owner): the feet catch up
	local animator = humanoid and humanoid:FindFirstChildOfClass("Animator")
	if animator then
		animator.AnimationPlayed:Connect(function(track)
			local anim = track.Animation
			if anim and STEP_IDS[anim.AnimationId] then
				rig.stepUntil = os.clock() + STEP_TIME
			end
		end)
	end
	character.Destroying:Connect(function()
		rigs[character] = nil
	end)
	return rig
end

local function wrap(a: number): number
	return (a + math.pi) % (2 * math.pi) - math.pi
end

-- How far the hips turn for this character now: full stance standing, less while moving.
local function stanceTurn(r: Rig, dt: number): number
	local s = Config.Weapons.AimStance or { Still = 0, Moving = 0 }
	local v = r.root.AssemblyLinearVelocity
	local moving = math.clamp(Vector3.new(v.X, 0, v.Z).Magnitude / 6, 0, 1)
	local want = math.rad(s.Still + (s.Moving - s.Still) * moving)
	r.turn += (want - r.turn) * math.min(1, dt * 8)
	return r.turn
end

local function stepTrack(r: Rig, dir: number): AnimationTrack?
	if not r.steps then
		local steps = {}
		local animator = r.humanoid and r.humanoid:FindFirstChildOfClass("Animator")
		for d, name in { [-1] = "Tulevo_TurnStepLeft", [1] = "Tulevo_TurnStepRight" } do
			local id = (AnimIds :: any)[name]
			if animator and id then
				local a = Instance.new("Animation")
				a.AnimationId = id
				local t = animator:LoadAnimation(a)
				t.Priority = Enum.AnimationPriority.Movement
				t.Looped = false
				steps[d] = t
			end
		end
		r.steps = steps
	end
	return (r.steps :: any)[dir]
end

-- Planted feet: returns how far (radians, + = left) the feet trail the body's facing.
local function plantFeet(r: Rig, dt: number, planted: boolean, isMe: boolean): number
	local _, yaw = r.root.CFrame:ToOrientation()
	if not planted or r.feetYaw == nil then
		r.feetYaw = if planted then yaw else nil
		r.lastYaw, r.still = yaw, 0
		return 0
	end
	local lag = wrap((r.feetYaw :: number) - yaw)
	if os.clock() < r.stepUntil then
		lag *= math.exp(-dt * 10) -- mid-step: the feet catch up with the body
	elseif isMe then
		local turning = math.abs(wrap(yaw - r.lastYaw)) > dt * math.rad(25)
		r.still = if turning then 0 else r.still + dt
		local step = Config.Weapons.AimStep or { Turn = 40, Settle = 14 }
		if math.abs(lag) > math.rad(step.Turn) or (math.abs(lag) > math.rad(step.Settle) and r.still > 0.15) then
			-- the body has turned left of the feet when lag < 0: the left foot steps first
			local t = stepTrack(r, if lag < 0 then -1 else 1)
			r.stepUntil = os.clock() + STEP_TIME
			if t then
				t:Play(0.08, 1, 1)
			end
		end
	end
	lag = math.clamp(lag, -MAX_LAG, MAX_LAG)
	r.feetYaw = yaw + lag
	r.lastYaw = yaw
	return lag
end

-- hipTurn: radians the hips (and legs) turn right of the root part's facing
local function lock(r: Rig, blend: number, pitch: number, hipTurn: number)
	if blend < 0.01 then
		return
	end
	local _, yaw = r.root.CFrame:ToOrientation()
	local target = CFrame.Angles(0, yaw, 0) * CFrame.Angles(pitch, 0, 0) * AIM_UT
	local lr = r.lowerRoot
	-- hips and legs into the stance: turn about the root part's up axis at the hip joint
	if math.abs(hipTurn * blend) > 0.001 then
		local c0 = lr.C0.Rotation
		lr.Transform = c0:Inverse() * CFrame.Angles(0, -hipTurn * blend, 0) * c0 * lr.Transform
	end
	local lowerTorso = r.root.CFrame * lr.C0 * lr.Transform * lr.C1:Inverse()
	local base = (lowerTorso * r.waist.C0).Rotation
	local anim = r.waist.Transform
	local locked = CFrame.new(anim.Position) * base:Inverse() * target * r.waist.C1.Rotation
	r.waist.Transform = if blend >= 0.999 then locked else anim:Lerp(locked, blend)
end

-- Lean pose. lean is -1..1 (+ = right); pitch is how much aim pitch the chest has (0 with the
-- gun down). Every turn is a world rotation about that joint, applied on top of the animation.
local LEAN_MAX = math.rad(Config.Weapons.LeanAngle or 25)
local HIP_SHARE = 0.3 -- of the lean taken by the hips (the chest does the rest)
local HEAD_BACK = 0.4 -- of the lean the head tilts back toward level

local function partOf(parent: CFrame, m: Motor6D): CFrame
	return parent * m.C0 * m.Transform * m.C1:Inverse()
end

local function turnJoint(m: Motor6D, parent: CFrame, rot: CFrame)
	local joint = parent * m.C0
	local pivot = (joint * m.Transform).Position
	local turn = CFrame.new(pivot) * rot * CFrame.new(-pivot)
	m.Transform = joint:Inverse() * turn * joint * m.Transform
end

local function applyLean(r: Rig, lean: number, pitch: number)
	if math.abs(lean) < 0.001 then
		return
	end
	local angle = lean * LEAN_MAX
	local _, yaw = r.root.CFrame:ToOrientation()
	local flat = CFrame.Angles(0, yaw, 0).LookVector
	local aim = (CFrame.Angles(0, yaw, 0) * CFrame.Angles(pitch, 0, 0)).LookVector
	-- hips tip toward the lean; the legs turn back so they stay upright
	local hip = CFrame.fromAxisAngle(flat, angle * HIP_SHARE)
	turnJoint(r.lowerRoot, r.root.CFrame, hip)
	local lowerTorso = partOf(r.root.CFrame, r.lowerRoot)
	for _, m in r.hips do
		turnJoint(m, lowerTorso, hip:Inverse())
	end
	-- chest: the rest, so in total it has turned exactly the lean round the aim direction
	local chest = CFrame.fromAxisAngle(aim, angle)
	turnJoint(r.waist, lowerTorso, chest * hip:Inverse())
	-- head tilts back toward level a little
	if r.neck then
		turnJoint(r.neck, partOf(lowerTorso, r.waist), CFrame.fromAxisAngle(aim, -angle * HEAD_BACK))
	end
end

local function standingStill(r: Rig): boolean
	local v = r.root.AssemblyLinearVelocity
	local h = r.humanoid
	return Vector3.new(v.X, 0, v.Z).Magnitude < 1 and h ~= nil and h.FloorMaterial ~= Enum.Material.Air
end

function GunPose.start()
	local me = Players.LocalPlayer
	RunService.PreSimulation:Connect(function(dt)
		for _, p in Players:GetPlayers() do
			local c = p.Character
			if not c then
				continue
			end
			if p == me then
				local r = if State.AimBlend > 0.01 then rigOf(c) else nil
				if r then
					local turn = stanceTurn(r, dt)
					local lag = plantFeet(r, dt, State.FeetPlant and standingStill(r), true)
					State.HipTurn = (turn - lag) * State.AimBlend
					lock(r, State.AimBlend, State.Pitch, turn - lag)
				else
					State.HipTurn = 0
					local old = rigs[c]
					if old then
						old.feetYaw = nil
					end
				end
				if State.Lean ~= 0 then
					local lr = r or rigOf(c)
					if lr then
						applyLean(lr, State.Lean, State.Pitch * State.AimBlend)
					end
				end
			else
				local up = c:GetAttribute("GunUp") == true
				local lean = c:GetAttribute("GunLean")
				lean = if typeof(lean) == "number" then math.clamp(lean, -1, 1) else 0
				local r = (up or lean ~= 0 or rigs[c]) and rigOf(c)
				if r then
					r.lean += (lean - r.lean) * math.min(1, dt * 12)
					if math.abs(r.lean) < 0.002 and lean == 0 then
						r.lean = 0
					end
					local k = math.min(1, dt * 12)
					r.blend += ((if up then 1 else 0) - r.blend) * k
					r.pitch += ((c:GetAttribute("GunPitch") or 0) - r.pitch) * k
					local planted = up and c:GetAttribute("GunPlant") == true and standingStill(r)
					local lag = plantFeet(r, dt, planted, false)
					lock(r, r.blend, r.pitch, stanceTurn(r, dt) - lag)
					applyLean(r, r.lean, r.pitch * r.blend)
				end
			end
		end
	end)
end

return GunPose
