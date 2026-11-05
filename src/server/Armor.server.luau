-- Every player wears the armor vest (Shared.ModelIds.ArmorVest) on spawn, welded to the UpperTorso.
-- It also gives the vest's armor points (Shared.Armor defs, ArmorVest = 50); damage goes
-- through Server.Damage, which takes covered hits off the armor before health.
-- The vest is modeled in studs around a default R15 UpperTorso (about 2 x 1.6 x 1), centered on it.
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

local function wear(character: Model)
	local humanoid = character:WaitForChild("Humanoid", 10) :: Humanoid?
	if humanoid then
		Damage.setArmor(humanoid, Armor.Default)
	end
	local torso = character:WaitForChild("UpperTorso", 10) :: BasePart?
	if not torso or not template then
		return
	end
	local old = character:FindFirstChild("ArmorVest")
	if old then
		old:Destroy()
	end
	local vest = template:Clone()
	vest:ScaleTo(torso.Size.X / TORSO_WIDTH)
	local boxCf = vest:GetBoundingBox()
	local fix = boxCf:ToObjectSpace(vest:GetPivot())
	local scale = vest:GetScale()
	local target = torso.CFrame * (BOX_OFFSET.Rotation + BOX_OFFSET.Position * scale)
	if FLIP then
		target *= CFrame.Angles(0, math.pi, 0)
	end
	vest:PivotTo(target * fix)
	for _, d in vest:GetDescendants() do
		if d:IsA("BasePart") then
			local weld = Instance.new("WeldConstraint")
			weld.Part0 = torso
			weld.Part1 = d
			weld.Parent = d
		end
	end
	vest.Parent = character
end

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
