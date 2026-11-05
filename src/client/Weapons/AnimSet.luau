--[[
	Loads a weapon class's animations onto the local character.
	Ids come from Shared.AnimIds as "Weapon_<Class>_<Slot>" (e.g. Weapon_Rifle_Reload).
	Slots without an id yet are skipped silently, so the system works before the art exists.

	Hold/Aim loop at Action priority (upper body over the walk/run legs); one-shots
	(Fire, Reload, Equip, Attack1..3) play at Action2 on top.
]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local AnimIds = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("AnimIds"))

local LOOPS = { Hold = true, Aim = true }

local AnimSet = {}
AnimSet.__index = AnimSet

function AnimSet.new(animator: Animator, class)
	local self = setmetatable({ tracks = {} }, AnimSet)
	for _, slot in class.Anims do
		local id = (AnimIds :: any)[`Weapon_{class.Name}_{slot}`]
		if id then
			local anim = Instance.new("Animation")
			anim.AnimationId = id
			local track = animator:LoadAnimation(anim)
			track.Looped = LOOPS[slot] == true
			track.Priority = if LOOPS[slot] then Enum.AnimationPriority.Action else Enum.AnimationPriority.Action2
			self.tracks[slot] = track
		end
	end
	return self
end

function AnimSet:play(slot: string, fade: number?, speed: number?)
	local t = self.tracks[slot]
	if t then
		t:Play(fade or 0.1, 1, speed or 1)
	end
	return t
end

function AnimSet:stop(slot: string, fade: number?)
	local t = self.tracks[slot]
	if t then
		t:Stop(fade or 0.15)
	end
end

function AnimSet:destroy()
	for _, t in self.tracks do
		t:Stop(0.15)
	end
	table.clear(self.tracks)
end

return AnimSet
