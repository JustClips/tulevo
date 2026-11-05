--[[
	Puts everyone aiming a gun into the rifle stance and locks their chest to the aim, on top
	of the animations.

	Stance (GTA): the whole body is bladed, not just the chest. The hips, and the legs with
	them, turn Config.Weapons.AimStance degrees right of the aim (less while moving), so the
	waist only twists the last few degrees. The root part still faces the aim, so the server's
	aim checks and the movement code don't change; Weapons/init picks the side-step blend
	relative to the turned hips (State.HipTurn).

	The Aim clip (art/anim/gun.py) shoulders the rifle with the chest bladed (AIM_UT below),
	but the chest hangs off the hips, and the walk/strafe clips bob, sway and turn the hips,
	so on its own the rifle would wobble with every step. Every frame, right after the
	animations are applied (PreSimulation), this sets the Waist joint so the UpperTorso has
	exactly the aim orientation in the world: facing yaw + aim pitch (up/down) + the blade.
	Arms, head and gun hang off the chest, so they're locked too.

	Local player: values from Weapons/State (AimBlend = how much of the Aim pose is in,
	Pitch). Other players: character attributes GunUp / GunPitch (server copies them from
	the Pose remote), smoothed here.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))

local State = require(script.Parent:WaitForChild("State"))

local GunPose = {}

-- UpperTorso pose of Weapon_Rifle_Aim relative to an upright body (gun.py AIM_TORSO)
local AIM_UT = CFrame.Angles(0, math.rad(-48), 0) * CFrame.Angles(math.rad(-4), 0, 0)

type Rig = {
	root: BasePart,
	lowerRoot: Motor6D,
	waist: Motor6D,
	blend: number,
	pitch: number,
	turn: number, -- smoothed hip turn (radians right of the aim)
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
	r = { root = root, lowerRoot = lowerRoot, waist = waist, blend = 0, pitch = 0, turn = 0 }
	rigs[character] = r
	character.Destroying:Connect(function()
		rigs[character] = nil
	end)
	return r
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

local function lock(r: Rig, blend: number, pitch: number, turn: number)
	if blend < 0.01 then
		return
	end
	local _, yaw = r.root.CFrame:ToOrientation()
	local target = CFrame.Angles(0, yaw, 0) * CFrame.Angles(pitch, 0, 0) * AIM_UT
	local lr = r.lowerRoot
	-- hips and legs into the stance: turn about the root part's up axis at the hip joint
	if turn * blend > 0.001 then
		local c0 = lr.C0.Rotation
		lr.Transform = c0:Inverse() * CFrame.Angles(0, -turn * blend, 0) * c0 * lr.Transform
	end
	local lowerTorso = r.root.CFrame * lr.C0 * lr.Transform * lr.C1:Inverse()
	local base = (lowerTorso * r.waist.C0).Rotation
	local anim = r.waist.Transform
	local locked = CFrame.new(anim.Position) * base:Inverse() * target * r.waist.C1.Rotation
	r.waist.Transform = if blend >= 0.999 then locked else anim:Lerp(locked, blend)
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
					State.HipTurn = turn * State.AimBlend
					lock(r, State.AimBlend, State.Pitch, turn)
				else
					State.HipTurn = 0
				end
			else
				local up = c:GetAttribute("GunUp") == true
				local r = (up or rigs[c]) and rigOf(c)
				if r then
					local k = math.min(1, dt * 12)
					r.blend += ((if up then 1 else 0) - r.blend) * k
					r.pitch += ((c:GetAttribute("GunPitch") or 0) - r.pitch) * k
					lock(r, r.blend, r.pitch, stanceTurn(r, dt))
				end
			end
		end
	end)
end

return GunPose
