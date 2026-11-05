--[[
	Loads a weapon class's animations onto the local character.
	Ids come from Shared.AnimIds as "Weapon_<Class>_<Slot>" (e.g. Weapon_Rifle_Reload).
	Slots without an id yet are skipped silently, so the system works before the art exists.

	Pose loops (Hold, Aim, Sprint, Tuck, Air, Lowered, CrouchHold) all play at once at Action2 priority
	and AnimSet:blend() cross-fades their weights, so switching pose never pops. They key the
	arms (Aim also the chest and head), so the legs keep the walk/run/roll/jump from Movement.
	One-shots (Fire, Reload, Equip, Draw, Holster, JumpPrep, JumpUp, Land, Attack1..3) play at
	Action3 on top.
]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local AnimIds = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("AnimIds"))

local LOOPS = { Hold = true, Aim = true, Sprint = true, Tuck = true, Air = true, Lowered = true, CrouchHold = true }
local MIN_WEIGHT = 0.001 -- loops keep running at ~0 weight so they can fade back in

local AnimSet = {}
AnimSet.__index = AnimSet

function AnimSet.new(animator: Animator, class)
	local self = setmetatable({ tracks = {}, weights = {}, sent = {} }, AnimSet)
	for _, slot in class.Anims do
		local id = (AnimIds :: any)[`Weapon_{class.Name}_{slot}`]
		if id then
			local anim = Instance.new("Animation")
			anim.AnimationId = id
			local track = animator:LoadAnimation(anim)
			track.Looped = LOOPS[slot] == true
			-- arms-only gun poses sit above the full-body jump wind-up (Action) so the hands stay
			-- on the gun; one-shots go on top of the poses
			track.Priority = if LOOPS[slot] then Enum.AnimationPriority.Action2 else Enum.AnimationPriority.Action3
			self.tracks[slot] = track
			if LOOPS[slot] then
				self.weights[slot] = 0
				track:Play(0, MIN_WEIGHT, 1)
			end
		end
	end
	return self
end

function AnimSet:has(slot: string): boolean
	return self.tracks[slot] ~= nil
end

-- Fade the pose loops toward target weights ({ Hold = 1 } etc.); missing slots fall back to Hold.
function AnimSet:blend(target: { [string]: number }, dt: number, rate: number?)
	local want = {}
	for slot, w in target do
		local s = if self.tracks[slot] then slot else "Hold"
		want[s] = (want[s] or 0) + w
	end
	local k = math.min(1, dt * (rate or 10))
	for slot, w in self.weights do
		w += ((want[slot] or 0) - w) * k
		self.weights[slot] = w
		local send = math.max(MIN_WEIGHT, w)
		if math.abs(send - (self.sent[slot] or -1)) > 0.01 or (send == MIN_WEIGHT and self.sent[slot] ~= MIN_WEIGHT) then
			self.tracks[slot]:AdjustWeight(send, 0.05)
			self.sent[slot] = send
		end
	end
end

function AnimSet:weight(slot: string): number
	return self.weights[slot] or 0
end

function AnimSet:play(slot: string, fade: number?, speed: number?)
	local t = self.tracks[slot]
	if t then
		if LOOPS[slot] then
			self.weights[slot] = 1
			t:AdjustWeight(1, fade or 0.1)
			self.sent[slot] = 1
		else
			t:Play(fade or 0.1, 1, speed or 1)
		end
	end
	return t
end

function AnimSet:stop(slot: string, fade: number?)
	local t = self.tracks[slot]
	if t then
		if LOOPS[slot] then
			self.weights[slot] = 0
			t:AdjustWeight(MIN_WEIGHT, fade or 0.15)
			self.sent[slot] = MIN_WEIGHT
		else
			t:Stop(fade or 0.15)
		end
	end
end

function AnimSet:destroy()
	for _, t in self.tracks do
		t:Stop(0.2)
		-- free it after the fade: an Animator stops playing new clips once too many are loaded
		task.delay(0.3, t.Destroy, t)
	end
	table.clear(self.tracks)
	table.clear(self.weights)
end

return AnimSet
