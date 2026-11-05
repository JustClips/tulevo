--[[
	Spawns every player as an R15 character built from their own avatar, so the GTA-style
	walk/run (Locomotion.client.luau) works for everyone:
	- R6 avatars are rebuilt as R15 (the walk/run clips are R15-only). If their avatar can't be
	  built, they get a plain R15 body; Roblox's own spawn (Game Settings avatar type, keep it
	  on R15) is only the last resort.
	- Avatar animation packs are removed, so idle/jump/fall always match our walk.
	- Body sizes and proportions are kept inside a normal human range (Config.Character).
	Clothes, skin colour, face, hair and accessories stay the player's own.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local StarterPlayer = game:GetService("StarterPlayer")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local Limits = Config.Character

Players.CharacterAutoLoads = false

local ANIM_FIELDS = {
	"IdleAnimation",
	"WalkAnimation",
	"RunAnimation",
	"JumpAnimation",
	"FallAnimation",
	"ClimbAnimation",
	"SwimAnimation",
	"MoodAnimation",
}

local function describe(player: Player, plain: boolean?): HumanoidDescription
	-- Studio test players have UserId <= 0 and get a plain body.
	local ok, desc = false, nil
	if player.UserId > 0 and not plain then
		ok, desc = pcall(function()
			return Players:GetHumanoidDescriptionFromUserId(player.UserId)
		end)
	end
	if not ok or not desc then
		desc = Instance.new("HumanoidDescription")
	end
	for _, field in ANIM_FIELDS do
		(desc :: any)[field] = 0
	end
	desc.HeightScale = math.clamp(desc.HeightScale, Limits.HeightMin, Limits.HeightMax)
	desc.WidthScale = math.clamp(desc.WidthScale, Limits.WidthMin, Limits.WidthMax)
	desc.DepthScale = math.clamp(desc.DepthScale, Limits.WidthMin, Limits.WidthMax)
	desc.HeadScale = math.clamp(desc.HeadScale, Limits.HeadMin, Limits.HeadMax)
	desc.BodyTypeScale = math.min(desc.BodyTypeScale, Limits.BodyTypeMax)
	desc.ProportionScale = math.min(desc.ProportionScale, Limits.ProportionMax)
	return desc
end

local function spawnCFrame(): CFrame
	local spawns = {}
	for _, obj in workspace:GetDescendants() do
		if obj:IsA("SpawnLocation") and obj.Enabled then
			table.insert(spawns, obj)
		end
	end
	if #spawns == 0 then
		return CFrame.new(0, 10, 0)
	end
	local s = spawns[math.random(1, #spawns)]
	local offset = Vector3.new((math.random() - 0.5) * s.Size.X * 0.6, 0, (math.random() - 0.5) * s.Size.Z * 0.6)
	return s.CFrame * CFrame.new(offset) + Vector3.new(0, s.Size.Y / 2 + 3.5, 0)
end

local function addRegen(humanoid: Humanoid)
	-- Same as Roblox's default Health script: 1% of max health per second.
	task.spawn(function()
		while humanoid.Parent and humanoid.Health > 0 do
			task.wait(1)
			if humanoid.Health > 0 and humanoid.Health < humanoid.MaxHealth then
				humanoid.Health = math.min(humanoid.MaxHealth, humanoid.Health + humanoid.MaxHealth * 0.01)
			end
		end
	end)
end

local spawnPlayer

local function build(player: Player, plain: boolean?)
	if not player.Parent then
		return
	end
	local character = Players:CreateHumanoidModelFromDescription(describe(player, plain), Enum.HumanoidRigType.R15)
	character.Name = player.Name
	local humanoid = character:FindFirstChildOfClass("Humanoid") :: Humanoid
	humanoid.DisplayName = player.DisplayName

	local hasHealth = false
	for _, item in StarterPlayer.StarterCharacterScripts:GetChildren() do
		if item.Name == "Health" then
			hasHealth = true
		end
		if not character:FindFirstChild(item.Name) then
			item:Clone().Parent = character
		end
	end

	local old = player.Character
	character:PivotTo(spawnCFrame())
	player.Character = character
	character.Parent = workspace
	if old and old ~= character then
		old:Destroy()
	end
	local root = character:FindFirstChild("HumanoidRootPart") :: BasePart
	if root and root:CanSetNetworkOwnership() then
		root:SetNetworkOwner(player)
	end
	if not hasHealth then
		addRegen(humanoid)
	end

	humanoid.Died:Once(function()
		task.wait(Players.RespawnTime)
		if player.Parent and player.Character == character then
			spawnPlayer(player)
		end
	end)
end

function spawnPlayer(player: Player)
	local ok, err = pcall(build, player)
	if not ok then
		-- still R15: a plain body instead of their avatar
		warn(`[CharacterSetup] custom spawn failed for {player.Name}: {err}; trying a plain R15 body`)
		ok, err = pcall(build, player, true)
	end
	if not ok then
		warn(`[CharacterSetup] plain R15 spawn failed for {player.Name}: {err}; using Roblox's default`)
		player:LoadCharacter()
	end
end

Players.PlayerAdded:Connect(spawnPlayer)
for _, player in Players:GetPlayers() do
	task.spawn(spawnPlayer, player)
end
