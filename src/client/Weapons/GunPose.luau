--[[
	Turns the waist of everyone holding a gun on top of their animations, so the rifle points
	where they aim: pitch (up/down) and twist (chest toward the camera while the hips follow
	the stick when strafing). It edits Waist.C0, which multiplies with the animation, so it
	works with any clip.

	The local player's values come from Weapons/State (set by the controller every frame);
	other players' come from their character attributes GunTwist / GunPitch (the server copies
	them from the Pose remote) and are smoothed here.
]]

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local State = require(script.Parent:WaitForChild("State"))

local GunPose = {}

local PITCH_WAIST = 0.75 -- share of the aim pitch done by the waist; the head does the rest
local rigs: { [Model]: { waist: Motor6D, neck: Motor6D?, c0: CFrame, neckC0: CFrame?, twist: number, pitch: number } } = {}

local function rigOf(character: Model)
	local r = rigs[character]
	if r and r.waist.Parent then
		return r
	end
	local ut = character:FindFirstChild("UpperTorso")
	local head = character:FindFirstChild("Head")
	local waist = ut and ut:FindFirstChild("Waist")
	local neck = head and head:FindFirstChild("Neck")
	if not waist or not waist:IsA("Motor6D") then
		return nil
	end
	r = {
		waist = waist,
		neck = if neck and neck:IsA("Motor6D") then neck else nil,
		c0 = waist.C0,
		neckC0 = if neck and neck:IsA("Motor6D") then neck.C0 else nil,
		twist = 0,
		pitch = 0,
	}
	rigs[character] = r
	character.Destroying:Connect(function()
		rigs[character] = nil
	end)
	return r
end

local function apply(r, twist: number, pitch: number, dt: number, smooth: number)
	local k = math.min(1, dt * smooth)
	r.twist += (twist - r.twist) * k
	r.pitch += (pitch - r.pitch) * k
	if math.abs(r.twist) < 1e-3 and math.abs(r.pitch) < 1e-3 and twist == 0 and pitch == 0 then
		r.twist, r.pitch = 0, 0
	end
	r.waist.C0 = r.c0 * CFrame.Angles(0, r.twist, 0) * CFrame.Angles(r.pitch * PITCH_WAIST, 0, 0)
	if r.neck and r.neckC0 then
		r.neck.C0 = r.neckC0 * CFrame.Angles(r.pitch * (1 - PITCH_WAIST), 0, 0)
	end
end

function GunPose.start()
	local me = Players.LocalPlayer
	RunService.RenderStepped:Connect(function(dt)
		for _, p in Players:GetPlayers() do
			local c = p.Character
			if not c then
				continue
			end
			if p == me then
				local r = (State.Twist ~= 0 or State.Pitch ~= 0 or rigs[c]) and rigOf(c)
				if r then
					apply(r, State.Twist, State.Pitch, dt, 30)
				end
			else
				local twist = c:GetAttribute("GunTwist") or 0
				local pitch = c:GetAttribute("GunPitch") or 0
				local r = (twist ~= 0 or pitch ~= 0 or rigs[c]) and rigOf(c)
				if r then
					apply(r, twist, pitch, dt, 12)
				end
			end
		end
	end)
end

return GunPose
