--[[
	Armor vest on the character (server).

	Every player wears the armor vest (Shared.ModelIds.ArmorVest) on spawn, welded to the
	UpperTorso, with the vest's armor points (Shared.Armor defs, ArmorVest = 50); damage goes
	through Server.Damage, which takes covered hits off the armor before health.

	Taking it off / putting it back on (client: V, gamepad D-pad up, phone Vest button; the
	"Vest" remote in ReplicatedStorage.ArmorRemotes). The client plays Tulevo_VestOff / VestOn
	(art/anim/vest.py) and this moves the real vest model on the same beats:
	  Off: lift  -> vest welded to the right hand, armor off (kept as StoredArmorItem /
	                StoredArmor on the Humanoid), stow -> vest gone.
	  On:  appear -> vest in the right hand, worn -> welded to the UpperTorso, the stored armor
	                back on.
	Hands must be free (no gun in the right hand: the client holsters it first).

	The vest is modeled in studs around a default R15 UpperTorso (about 2 x 1.6 x 1); its
	bounding box centre sits BOX_OFFSET from the torso centre.
]]

local InsertService = game:GetService("InsertService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local ModelIds = require(Shared:WaitForChild("ModelIds"))
local Armor = require(Shared:WaitForChild("Armor"))
local Damage = require(script.Parent:WaitForChild("Damage"))

local TORSO_WIDTH = 2 -- UpperTorso width the vest was built for
-- Vest box center relative to the torso center (from art/models/ArmorVest/meta.json):
-- 0.1025 down (long cut reaching the belt), 0.0275 forward (forward = -Z).
local BOX_OFFSET = CFrame.new(0, -0.1025, -0.0275)
-- Set to true if the vest shows up backwards on the character.
local FLIP = false
-- RightHand -> vest box centre while carried (art/anim/vest.py prints VEST_IN_HAND)
local VEST_IN_HAND = CFrame.new(-1.1, 0.2719, -0.4446, 0, 1, 0, -0.5, 0, 0.866, 0.866, 0, 0.5)
-- beats in seconds (art/anim/vest.py VEST_ON / VEST_OFF)
local ON = { appear = 0.15, worn = 0.85, length = 1.75 }
local OFF = { lift = 0.5, stow = 1.1, length = 1.35 }

local remotes = Instance.new("Folder")
remotes.Name = "ArmorRemotes"
local VestRemote = Instance.new("RemoteEvent")
VestRemote.Name = "Vest"
VestRemote.Parent = remotes
remotes.Parent = ReplicatedStorage

local template: Model? = nil

local function loadTemplate(): Model?
	local def = Armor.get(Armor.Default)
	local id = def and def.Model and ModelIds[def.Model]
	if not id then
		return nil
	end
	local ok, container = pcall(InsertService.LoadAsset, InsertService, id)
	if not ok then
		warn(`[Armor] could not load the vest ({id}): {container}`)
		return nil
	end
	local model = Instance.new("Model")
	model.Name = "ArmorVest"
	for _, child in container:GetChildren() do
		child.Parent = model
	end
	container:Destroy()
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.Anchored = false
			d.CanCollide = false
			d.CanQuery = false
			d.CanTouch = false
			d.Massless = true
			d.CastShadow = true
		elseif d:IsA("Script") or d:IsA("LocalScript") or d:IsA("JointInstance") or d:IsA("WeldConstraint") then
			d:Destroy()
		end
	end
	return model
end

local function flip(cf: CFrame): CFrame
	return if FLIP then cf * CFrame.Angles(0, math.pi, 0) else cf
end

-- Torso -> vest box centre when worn, and hand -> box centre when carried, for this torso.
local function offsets(torso: BasePart): (CFrame, CFrame, number)
	local scale = torso.Size.X / TORSO_WIDTH
	local worn = flip(BOX_OFFSET.Rotation + BOX_OFFSET.Position * scale)
	local hand = flip(VEST_IN_HAND.Rotation + VEST_IN_HAND.Position * scale)
	return worn, hand, scale
end

local function setWelds(vest: Model, part0: BasePart, c0: CFrame)
	for _, d in vest:GetDescendants() do
		if d:IsA("Weld") and d.Name == "VestWeld" then
			d.Part0, d.C0 = part0, c0
		end
	end
end

-- A fresh vest welded to part0 at c0 (box centre frame).
local function makeVest(character: Model, part0: BasePart, c0: CFrame, scale: number): Model?
	if not template then
		return nil
	end
	local old = character:FindFirstChild("ArmorVest")
	if old then
		old:Destroy()
	end
	local vest = template:Clone()
	vest:ScaleTo(scale)
	local box = vest:GetBoundingBox()
	for _, d in vest:GetDescendants() do
		if d:IsA("BasePart") then
			local weld = Instance.new("Weld")
			weld.Name = "VestWeld"
			weld.Part0 = part0
			weld.Part1 = d
			weld.C0 = c0
			weld.C1 = box:ToObjectSpace(d.CFrame):Inverse()
			weld.Parent = d
		end
	end
	vest.Parent = character
	return vest
end

local function wear(character: Model)
	local humanoid = character:WaitForChild("Humanoid", 10) :: Humanoid?
	if humanoid then
		Damage.setArmor(humanoid, Armor.Default)
	end
	local torso = character:WaitForChild("UpperTorso", 10) :: BasePart?
	if not torso then
		return
	end
	local worn, _, scale = offsets(torso)
	makeVest(character, torso, worn, scale)
end

-- Take the vest off / put it back on, in time with the client's clip.
local busy: { [Humanoid]: boolean } = {}
VestRemote.OnServerEvent:Connect(function(player)
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	local torso = character and character:FindFirstChild("UpperTorso") :: BasePart?
	local hand = character and character:FindFirstChild("RightHand") :: BasePart?
	if not (character and humanoid and torso and hand) or humanoid.Health <= 0 or humanoid.SeatPart or busy[humanoid] then
		return
	end
	-- hands must be free
	local gun = character:FindFirstChild("Gun")
	local gunWeld = gun and gun:FindFirstChild("GunWeld", true)
	if gunWeld and gunWeld:IsA("Weld") and gunWeld.Part0 == hand then
		return
	end
	local worn, inHand, scale = offsets(torso)
	local function at(t: number, fn: () -> ())
		task.delay(t, function()
			if humanoid.Parent == character and humanoid.Health > 0 then
				fn()
			end
		end)
	end
	local wornItem = humanoid:GetAttribute("ArmorItem")
	if wornItem then
		busy[humanoid] = true
		at(OFF.lift, function()
			local vest = character:FindFirstChild("ArmorVest")
			if vest then
				setWelds(vest, hand, inHand)
			end
			humanoid:SetAttribute("StoredArmorItem", wornItem)
			humanoid:SetAttribute("StoredArmor", humanoid:GetAttribute("Armor") or 0)
			Damage.setArmor(humanoid, nil)
		end)
		at(OFF.stow, function()
			local vest = character:FindFirstChild("ArmorVest")
			if vest then
				vest:Destroy()
			end
		end)
	else
		local item = humanoid:GetAttribute("StoredArmorItem")
		if not item then
			return -- no vest to put on
		end
		busy[humanoid] = true
		local vest: Model? = nil
		at(ON.appear, function()
			vest = makeVest(character, hand, inHand, scale)
		end)
		at(ON.worn, function()
			if vest and vest.Parent then
				setWelds(vest, torso, worn)
			end
			local stored = humanoid:GetAttribute("StoredArmor")
			Damage.setArmor(humanoid, item)
			if typeof(stored) == "number" then
				humanoid:SetAttribute("Armor", math.clamp(stored, 0, humanoid:GetAttribute("MaxArmor") or 0))
			end
			humanoid:SetAttribute("StoredArmorItem", nil)
			humanoid:SetAttribute("StoredArmor", nil)
		end)
	end
	task.delay(if wornItem then OFF.length else ON.length, function()
		busy[humanoid] = nil
	end)
end)

local function onPlayer(player: Player)
	player.CharacterAdded:Connect(wear)
	if player.Character then
		task.spawn(wear, player.Character)
	end
end

template = loadTemplate()
Players.PlayerAdded:Connect(onPlayer)
for _, player in Players:GetPlayers() do
	onPlayer(player)
end
