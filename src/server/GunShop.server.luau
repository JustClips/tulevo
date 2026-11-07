--!strict
--[[
	Gun shop: Ironwood Arms (art/blender/gunshop, docs/gunshop.md).

	The building (City.Buildings[Config.GunShop.Building]) carries invisible marker parts:
		SpotBuy      the customer's spot at the till -> the "Shop" ProximityPrompt (E)
		SpotClerk    where the clerk stands, facing the customer
		SpotCam      the menu camera, looking at SpotCamLook (the gun wall)
	Server/CityBuildings hides them; this script waits for the model's CityReady attribute.

	Remotes (ReplicatedStorage.GunShopRemotes):
		Open  RemoteEvent     server -> client (shop): opens the buy menu
		Buy   RemoteFunction  client -> server (entry index) -> { ok, message, shop }
		Close RemoteEvent     client -> server: the menu closed

	The server decides everything: the player must be standing at the till with the menu open,
	alive, not knocked; the price comes from Config, money from Server/Money (cash first, the
	rest from the bank), items go in through InventoryService (a weapon item = owning the gun).
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Items = require(Shared:WaitForChild("Items"))
local Armor = require(Shared:WaitForChild("Armor"))
local ModelIds = require(Shared:WaitForChild("ModelIds"))
local Money = require(script.Parent:WaitForChild("Money"))
local Guard = require(script.Parent:WaitForChild("Guard"))
local InventoryService = require(script.Parent:WaitForChild("Inventory"):WaitForChild("InventoryService"))

local CFG = Config.GunShop

local remotes = Instance.new("Folder")
remotes.Name = "GunShopRemotes"
local OpenRemote = Instance.new("RemoteEvent")
OpenRemote.Name = "Open"
OpenRemote.Parent = remotes
local CloseRemote = Instance.new("RemoteEvent")
CloseRemote.Name = "Close"
CloseRemote.Parent = remotes
local BuyRemote = Instance.new("RemoteFunction")
BuyRemote.Name = "Buy"
BuyRemote.Parent = remotes
remotes.Parent = ReplicatedStorage

local shopping: { [Player]: boolean } = {}
local buyAt: Vector3? = nil -- world position of SpotBuy
local camCF: CFrame? = nil

-- "buy" | "owned" | "soldout" for one stock entry
local function stateOf(player: Player, entry): string
	local def = Items.get(entry.Id)
	if not def then
		return "soldout"
	end
	if def.Kind == "Weapon" then
		-- a gun is only sold once it has a model to hold
		if not (def.Model and (ModelIds :: any)[def.Model]) then
			return "soldout"
		end
		if InventoryService.count(player, entry.Id) > 0 then
			return "owned"
		end
	end
	return "buy"
end

local function shopFor(player: Player)
	local list = {}
	for i, entry in CFG.Stock do
		list[i] = {
			Index = i,
			Category = entry.Category,
			Id = entry.Id,
			Price = entry.Price,
			Count = entry.Count or 1,
			State = stateOf(player, entry),
		}
	end
	return {
		Name = CFG.Name,
		Categories = CFG.Categories,
		Stock = list,
		Camera = camCF,
		At = buyAt,
	}
end

local function atTill(player: Player, extra: number): boolean
	local _, _, root = Guard.alive(player)
	return root ~= nil and buyAt ~= nil and (root.Position - (buyAt :: Vector3)).Magnitude <= CFG.LeaveDistance + extra
end

-- take price: cash first, then the bank. false (nothing taken) if they can't pay
local function charge(player: Player, price: number): boolean
	local cash, bank = Money.get(player)
	if cash >= price then
		return Money.addCash(player, -price)
	end
	if not CFG.PayFromBank or cash + bank < price then
		return false
	end
	local fromBank = price - cash
	if not Money.addBank(player, -fromBank) then
		return false
	end
	if cash > 0 and not Money.addCash(player, -cash) then
		Money.addBank(player, fromBank)
		return false
	end
	return true
end

local function buy(player: Player, index: any)
	if not shopping[player] then
		return { ok = false, message = "Walk up to the counter first" }
	end
	if not Guard.rate(player, "GunShopBuy", 4, 3) then
		return { ok = false, message = "Slow down" }
	end
	local i = Guard.number(index, 1, #CFG.Stock)
	local entry = i and CFG.Stock[math.floor(i :: number)]
	if not entry then
		return { ok = false, message = "Not for sale" }
	end
	if not atTill(player, 4) then
		shopping[player] = nil
		return { ok = false, message = "You walked away from the counter" }
	end
	local def = Items.get(entry.Id)
	local state = stateOf(player, entry)
	if not def or state == "soldout" then
		return { ok = false, message = "Out of stock", shop = shopFor(player) }
	elseif state == "owned" then
		return { ok = false, message = `You already own a {def.Name}`, shop = shopFor(player) }
	end
	local cash, bank = Money.get(player)
	if cash + (if CFG.PayFromBank then bank else 0) < entry.Price then
		return { ok = false, message = "Not enough money", shop = shopFor(player) }
	end
	-- goods first (so a full bag costs nothing), then the money; undo the goods if paying fails
	local count = entry.Count or 1
	local data = nil
	if def.Kind == "Armor" then
		local ad = Armor.get(entry.Id)
		data = { armor = if ad then ad.MaxArmor else 50 }
	end
	local left = InventoryService.add(player, entry.Id, count, data)
	if left > 0 then
		if count - left > 0 then
			InventoryService.remove(player, entry.Id, count - left)
		end
		return { ok = false, message = "No room in your bag", shop = shopFor(player) }
	end
	if not charge(player, entry.Price) then
		InventoryService.remove(player, entry.Id, count)
		return { ok = false, message = "Not enough money", shop = shopFor(player) }
	end
	local what = if count > 1 then `{count} x {def.Name}` else def.Name
	return { ok = true, message = `Bought {what}`, shop = shopFor(player) }
end

BuyRemote.OnServerInvoke = function(player: Player, index: any)
	local ok, result = pcall(buy, player, index)
	if not ok then
		warn(`[GunShop] buy failed for {player.Name}: {result}`)
		return { ok = false, message = "Something went wrong" }
	end
	return result
end

CloseRemote.OnServerEvent:Connect(function(player: Player)
	shopping[player] = nil
end)
Players.PlayerRemoving:Connect(function(player)
	shopping[player] = nil
end)

---------------------------------------------------------------- clerk

local function makeClerk(model: Model, at: BasePart, face: Vector3)
	local desc = Instance.new("HumanoidDescription")
	desc.HeadColor = Color3.fromRGB(198, 150, 112)
	desc.LeftArmColor = desc.HeadColor
	desc.RightArmColor = desc.HeadColor
	desc.TorsoColor = Color3.fromRGB(46, 50, 44) -- dark olive staff shirt
	desc.LeftLegColor = Color3.fromRGB(58, 52, 44)
	desc.RightLegColor = desc.LeftLegColor
	local ok, clerk = pcall(function()
		return Players:CreateHumanoidModelFromDescription(desc, Enum.HumanoidRigType.R15)
	end)
	if not ok or not clerk then
		warn(`[GunShop] no clerk: {clerk}`)
		return
	end
	clerk.Name = "Clerk"
	local hum = clerk:FindFirstChildOfClass("Humanoid") :: Humanoid
	hum.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
	hum.HealthDisplayType = Enum.HumanoidHealthDisplayType.AlwaysOff
	hum.BreakJointsOnDeath = false
	hum:SetStateEnabled(Enum.HumanoidStateType.Dead, false)
	local animate = clerk:FindFirstChild("Animate")
	if animate then
		animate:Destroy()
	end
	local root = clerk:FindFirstChild("HumanoidRootPart") :: BasePart
	root.Anchored = true
	for _, d in clerk:GetDescendants() do
		if d:IsA("BasePart") then
			d.CanCollide = false
			d.CanQuery = d.Name ~= "HumanoidRootPart"
		end
	end
	local floorY = at.Position.Y - at.Size.Y / 2
	local height = hum.HipHeight + root.Size.Y / 2
	local pos = Vector3.new(at.Position.X, floorY + height, at.Position.Z)
	local look = Vector3.new(face.X, pos.Y, face.Z)
	clerk:PivotTo(CFrame.lookAt(pos, look))
	clerk:SetAttribute("GunShopClerk", true)
	clerk.Parent = model
end

---------------------------------------------------------------- setup

local function find(model: Model, name: string): BasePart?
	local p = model:FindFirstChild(name, true)
	return if p and p:IsA("BasePart") then p else nil
end

local function setup(model: Model)
	local spotBuy, spotClerk = find(model, "SpotBuy"), find(model, "SpotClerk")
	local spotCam, spotLook = find(model, "SpotCam"), find(model, "SpotCamLook")
	if not (spotBuy and spotClerk) then
		warn("[GunShop] SpotBuy / SpotClerk missing in", model:GetFullName())
		return
	end
	local floorY = spotBuy.Position.Y - spotBuy.Size.Y / 2
	buyAt = Vector3.new(spotBuy.Position.X, floorY + 2.5, spotBuy.Position.Z)
	if spotCam and spotLook then
		camCF = CFrame.lookAt(spotCam.Position, spotLook.Position)
	end
	makeClerk(model, spotClerk, spotBuy.Position)

	local att = Instance.new("Attachment")
	att.Name = "GunShopBuy"
	att.WorldPosition = buyAt :: Vector3
	att.Parent = spotBuy
	local prompt = Instance.new("ProximityPrompt")
	prompt.Name = "GunShopPrompt"
	prompt.ActionText = "Shop"
	prompt.ObjectText = CFG.Name
	prompt.KeyboardKeyCode = Enum.KeyCode.E
	prompt.HoldDuration = 0
	prompt.MaxActivationDistance = CFG.UseDistance
	prompt.RequiresLineOfSight = false
	prompt.Parent = att
	prompt.Triggered:Connect(function(player: Player)
		if not Guard.rate(player, "GunShopOpen", 2, 2) or not atTill(player, 0) then
			return
		end
		shopping[player] = true
		OpenRemote:FireClient(player, shopFor(player))
	end)
	print("[GunShop] ready")
end

local city = workspace:WaitForChild("City", 30)
local buildings = city and city:WaitForChild("Buildings", 30)
local model = buildings and buildings:WaitForChild(CFG.Building, 30)
if not (model and model:IsA("Model")) then
	warn(`[GunShop] building {CFG.Building} not found`)
	return
end
if not model:GetAttribute("CityReady") then
	model:GetAttributeChangedSignal("CityReady"):Wait()
end
setup(model)
