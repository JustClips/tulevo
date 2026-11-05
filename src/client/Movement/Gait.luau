--[[
	The foot animation layer: Walk, Jog and Sprint clips (art/anim/locomotion.py) played at
	Movement priority above the default Animate script. Weights blend by real speed between
	each gait's reference speed (Config.Movement), and every clip plays at
	speed / Natural so the planted foot moves with the ground.
]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local Gaits = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Gaits"))
-- aiming while walking backwards plays the clips in reverse (set by Client.Weapons)
local WeaponState = require(Players.LocalPlayer:WaitForChild("PlayerScripts"):WaitForChild("Client"):WaitForChild("Weapons"):WaitForChild("State"))

-- Aiming side-steps (art/anim/strafe.py): studs/s the clip covers at playback speed 1
local STRAFE_NATURAL = 3.125
local STRAFE_CLIPS = { Right = "Tulevo_StrafeRight", Left = "Tulevo_StrafeLeft" }
local MAX_RATE = 2.3 -- faster than this looks frantic; a little foot slide reads better
local DEFAULT_GROUND = 3.19 -- default R15: HipHeight 2.19 + half the root part

local Gait = {}
Gait.__index = Gait

function Gait.new(ctx)
	local m = ctx.Config.Movement
	local refs = { Walk = m.WalkSpeed, Jog = m.JogSpeed, Sprint = m.SprintSpeed }
	local self = setmetatable({ ctx = ctx, layers = {}, weight = 0 }, Gait)
	for _, g in Gaits do
		local track = ctx.LoadClip(g.Clip)
		track.Priority = Enum.AnimationPriority.Movement
		track.Looped = true
		track:Play(0, 0.001, 1)
		table.insert(self.layers, { track = track, natural = g.Natural, ref = refs[g.Name] or m.WalkSpeed, w = 0, sent = -1 })
	end
	-- while aiming, moving sideways blends in side-step clips (the body keeps facing the aim)
	self.strafe = {}
	for dir, clip in STRAFE_CLIPS do
		local ok, track = pcall(ctx.LoadClip, clip)
		if ok then
			track.Priority = Enum.AnimationPriority.Movement
			track.Looped = true
			track:Play(0, 0.001, 1)
			self.strafe[dir] = { track = track, w = 0, sent = -1 }
		end
	end
	return self
end

-- weight of each layer at this speed: linear between neighbouring reference speeds
local function shares(layers, speed)
	local out = table.create(#layers, 0)
	if speed <= layers[1].ref then
		out[1] = 1
		return out
	end
	for i = 1, #layers - 1 do
		local a, b = layers[i].ref, layers[i + 1].ref
		if speed <= b then
			local t = (speed - a) / math.max(0.01, b - a)
			out[i], out[i + 1] = 1 - t, t
			return out
		end
	end
	out[#layers] = 1
	return out
end

function Gait:update(dt: number, enabled: boolean)
	local ctx = self.ctx
	local on = enabled and ctx.Grounded and ctx.Wants and ctx.Speed > 0.6
	self.weight += ((if on then 1 else 0) - self.weight) * math.min(1, dt * 12)

	local size = (ctx.Humanoid.HipHeight + ctx.Root.Size.Y / 2) / DEFAULT_GROUND
	-- share of the movement that is sideways while aiming (signed: + right), set by Client.Weapons
	local side = math.clamp(WeaponState.StrafeSide or 0, -1, 1)
	local forward = 1 - math.abs(side)
	for dir, l in self.strafe do
		local want = if dir == "Right" then math.max(0, side) else math.max(0, -side)
		l.w += (want - l.w) * math.min(1, dt * 10)
		l.track:AdjustSpeed(math.clamp(math.max(ctx.Speed, 1) / (STRAFE_NATURAL * size), 0.5, MAX_RATE))
		local w = math.max(0.001, self.weight * l.w)
		if math.abs(w - l.sent) > 0.01 then
			l.track:AdjustWeight(w, 0)
			l.sent = w
		end
	end
	local want = shares(self.layers, ctx.Speed)
	local lead = self.layers[1]
	for _, l in self.layers do
		if l.w > lead.w then
			lead = l
		end
	end
	for i, l in self.layers do
		local before = l.w
		l.w += (want[i] - l.w) * math.min(1, dt * 8)
		-- a clip fading in starts on the same step as the one leading now
		if before < 0.02 and l.w >= 0.02 and l ~= lead and lead.track.Length > 0 and l.track.Length > 0 then
			l.track.TimePosition = (lead.track.TimePosition / lead.track.Length) * l.track.Length
		end
		local rate = math.clamp(math.max(ctx.Speed, 1) / (l.natural * size), 0.5, MAX_RATE)
		l.track:AdjustSpeed(if WeaponState.GaitReverse then -rate else rate)
		local w = math.max(0.001, self.weight * l.w * forward)
		if math.abs(w - l.sent) > 0.01 then
			l.track:AdjustWeight(w, 0)
			l.sent = w
		end
	end
end

function Gait:stop()
	for _, l in self.layers do
		l.track:Stop(0.2)
	end
	for _, l in self.strafe do
		l.track:Stop(0.2)
	end
end

return Gait
