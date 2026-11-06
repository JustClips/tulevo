--[[
	Item use sounds: while anyone uses an item (Player attribute UsingItemId, set by the server's
	InventoryService), its Use.Sound (Shared/Items/Defs) plays on their character. Stops early if
	the use is cancelled. Sounds from tools/use_sounds.py; volume in Config.UseSounds.
]]
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Items = require(Shared:WaitForChild("Items"))
local SoundIds = require(Shared:WaitForChild("SoundIds"))

local playing: { [Player]: Sound } = {}

local function stop(p: Player)
	local s = playing[p]
	playing[p] = nil
	if s then
		s:Stop()
		s:Destroy()
	end
end

local function update(p: Player)
	stop(p)
	local id = p:GetAttribute("UsingItemId")
	local def = id and Items.get(id)
	local name = def and def.Use and (def.Use :: any).Sound
	local soundId = name and (SoundIds :: any)[name]
	local head = p.Character and p.Character:FindFirstChild("Head")
	if not soundId or not head then
		return
	end
	local cfg = Config.UseSounds
	local s = Instance.new("Sound")
	s.SoundId = "rbxassetid://" .. soundId
	s.Volume = cfg.Volume
	s.RollOffMode = Enum.RollOffMode.InverseTapered
	s.RollOffMinDistance = 6
	s.RollOffMaxDistance = cfg.MaxDistance
	s.Parent = head
	s.Ended:Connect(function()
		if playing[p] == s then
			playing[p] = nil
		end
		s:Destroy()
	end)
	playing[p] = s
	s:Play()
end

local function watch(p: Player)
	p:GetAttributeChangedSignal("UsingItemId"):Connect(function()
		update(p)
	end)
	p.CharacterAdded:Connect(function()
		stop(p)
	end)
end

for _, p in Players:GetPlayers() do
	watch(p)
end
Players.PlayerAdded:Connect(watch)
Players.PlayerRemoving:Connect(stop)
