--[[
	Server-side inventory. The server owns every player's items; the client only asks to move
	things and draws what it's sent (Client/Inventory).

	Each player has:
	  Inventory  Config.Inventory Cols x Rows grid, up to MaxWeight kg
	  Backpack   BackpackCols x BackpackRows grid, up to BackpackMaxWeight kg
	  Quick      QuickSlots slots (keys 1-3), one item each, any size; their weight counts
	             toward the Inventory's MaxWeight. The default weapons start here.
	  Armor      the worn vest (equipment slot; doesn't count toward weight)
	Items cover several cells (Shared/Items Cells: vest 2 x 2, carbine 4 x 2) and can be turned
	(rot). An item is { uid, id, count, rot?, data? } stored at its top-left slot. id is a Shared/Items id; data holds what travels with
	that one item (a gun's mag/reserve, a vest's armor points left).

	Weapons follow the items: carrying a gun item gives the weapon (Server/Weapons/
	WeaponService), dropping the last one takes it away (its ammo stays on the dropped item).
	The worn vest is moved in and out of the Armor slot by Server/Armor (V and dragging both go
	through the vest animation).

	Dropped items are Models in Workspace.DroppedItems (attributes Uid, ItemId, Count) with a
	"Pick up" prompt; they disappear after Config.Inventory.DroppedLifetime seconds.

		InventoryService.get(player)                -> the player's inventory (made with the starting kit)
		InventoryService.add(player, id, count?, data?) -> how many didn't fit
		InventoryService.count(player, id)          -> how many they carry
		InventoryService.remove(player, id, count)  -> how many it took out of the bag
		InventoryService.spawnPickup(id, count, cframe, data?) -> an item lying on the ground (debug, world loot)
		InventoryService.wornArmor(player)          -> Item?
		InventoryService.putOnArmor(player, uid?)   -> Item? (moved bag -> Armor slot)
		InventoryService.takeOffArmor(player, armorLeft) (Armor slot -> bag, or the ground if full)

	Remotes (ReplicatedStorage.InventoryRemotes):
		State   (server -> owner)  snapshot (see snapshot())
		Request (client -> server) send me my snapshot
		Move    (client -> server) from, fromKey, to, toKey, rot
		        from/to: "Inventory" | "Backpack" | "Quick" | "Ground"; keys are top-left slot
		        numbers (Shared/Items/Grid), quick slot numbers (1-3), or the dropped item's Uid
		        for "Ground" as from (toKey is ignored for "Ground"); rot = the item turned 90
		        degrees (R while dragging)
		Use     (client -> server) uid: use that carried item (Shared/Items Use; nil = stop using)
		Notice  (server -> owner)  text: why something was refused ("Already at full health")

	Using items: an item with Use = { Action = ..., Time = ... } (Shared/Items/Actions.luau).
	Server actions run from Server/Inventory/ItemUse.luau after Time seconds; while it runs the
	player has attributes UsingItem (item name), UseStart / UseEnd (workspace:GetServerTimeNow()),
	which Client/Inventory draws as a bar. It stops if the player is knocked down, dies, or the
	item leaves the bag; one item is taken when it finishes.

	Ammo: guns with Ammo = "<item id>" reload from those items (WeaponService.setAmmoSource).
]]

local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Items = require(Shared:WaitForChild("Items"))
local Grid = require(Shared:WaitForChild("Items"):WaitForChild("Grid"))
local Armor = require(Shared:WaitForChild("Armor"))
local Weapons = require(Shared:WaitForChild("Weapons"))
local WeaponService = require(script.Parent.Parent:WaitForChild("Weapons"):WaitForChild("WeaponService"))
local ItemModels = require(script.Parent:WaitForChild("ItemModels"))
local ItemUse = require(script.Parent:WaitForChild("ItemUse"))

local CFG = Config.Inventory

export type Item = { uid: string, id: string, count: number, rot: boolean?, data: { [string]: any }? }
type Inv = {
	Inventory: { [number]: Item },
	Backpack: { [number]: Item },
	Quick: { [number]: Item },
	Armor: Item?,
}

local CONTAINERS = {
	Inventory = { cols = CFG.Cols, rows = CFG.Rows, slots = CFG.Cols * CFG.Rows, max = CFG.MaxWeight },
	Backpack = {
		cols = CFG.BackpackCols,
		rows = CFG.BackpackRows,
		slots = CFG.BackpackCols * CFG.BackpackRows,
		max = CFG.BackpackMaxWeight,
	},
}
local ORDER = { "Inventory", "Backpack" } -- where new items go first
local QUICK = CFG.QuickSlots or 3

local remotes = Instance.new("Folder")
remotes.Name = "InventoryRemotes"
local function remote(name: string): RemoteEvent
	local r = Instance.new("RemoteEvent")
	r.Name = name
	r.Parent = remotes
	return r
end
local StateRemote = remote("State")
local RequestRemote = remote("Request")
local MoveRemote = remote("Move")
local UseRemote = remote("Use")
local NoticeRemote = remote("Notice")
remotes.Parent = ReplicatedStorage

local droppedFolder = Instance.new("Folder")
droppedFolder.Name = "DroppedItems"
droppedFolder.Parent = workspace

local InventoryService = {}

local invs: { [Player]: Inv } = {}
local dropped: { [string]: { item: Item, model: Model, expires: number } } = {}

local function newUid(): string
	return HttpService:GenerateGUID(false)
end

local function itemWeight(item: Item): number
	local def = Items.get(item.id)
	return (if def then def.Weight else 0) * item.count
end

local function weightOf(list: { [number]: Item }): number
	local w = 0
	for _, item in list do
		w += itemWeight(item)
	end
	return w
end

-- Weight limits: the quick slots are on you, so they share the Inventory's limit.
local function bucket(name: string): string
	return if name == "Quick" then "Inventory" else name
end

local function maxOf(name: string): number
	return CONTAINERS[bucket(name)].max
end

-- kg used toward this container's limit
local function used(inv: Inv, name: string): number
	local b = bucket(name)
	local w = weightOf((inv :: any)[b])
	if b == "Inventory" then
		w += weightOf(inv.Quick)
	end
	return w
end

-- how many more of this item fit by weight
local function roomByWeight(inv: Inv, name: string, weight: number): number
	if weight <= 0 then
		return math.huge
	end
	return math.max(0, math.floor((maxOf(name) - used(inv, name)) / weight + 1e-6))
end

-- First spot for an item in a container (as it is, else turned). Returns slot, rot.
local function spotFor(name: string, list: { [number]: Item }, id: string, rot: boolean?): (number?, boolean)
	local c = CONTAINERS[name]
	local w, h = Grid.baseSize(id)
	if rot then
		w, h = h, w
	end
	local slot = Grid.findSpot(list, c.cols, c.rows, w, h)
	if slot then
		return slot, rot == true
	end
	if w ~= h then
		slot = Grid.findSpot(list, c.cols, c.rows, h, w)
		if slot then
			return slot, not rot
		end
	end
	return nil, false
end

local function snapshot(inv: Inv)
	local out = { containers = {}, armor = inv.Armor or false }
	for name in CONTAINERS do
		local list = {}
		for slot, item in (inv :: any)[name] do
			table.insert(
				list,
				{ slot = slot, uid = item.uid, id = item.id, count = item.count, rot = item.rot, data = item.data }
			)
		end
		out.containers[name] = list
	end
	local quick = {}
	for slot, item in inv.Quick do
		table.insert(quick, { slot = slot, uid = item.uid, id = item.id, count = item.count, data = item.data })
	end
	out.quick = quick
	return out
end

local function allCarried(inv: Inv): { Item }
	local out = {}
	for i = 1, QUICK do
		if inv.Quick[i] then
			table.insert(out, inv.Quick[i])
		end
	end
	for _, name in ORDER do
		local list = (inv :: any)[name]
		for i = 1, CONTAINERS[name].slots do
			if list[i] then
				table.insert(out, list[i])
			end
		end
	end
	return out
end

-- Weapons the player may use = gun items they carry.
local function syncWeapons(player: Player, inv: Inv)
	local carried: { [string]: Item } = {}
	for _, item in allCarried(inv) do
		local def = Items.get(item.id)
		if def and def.Kind == "Weapon" and not carried[item.id] then
			carried[item.id] = item
		end
	end
	local have: { [string]: boolean } = {}
	for _, id in WeaponService.list(player) do
		have[id] = true
		if not carried[id] then
			WeaponService.take(player, id)
		end
	end
	for id, item in carried do
		if not have[id] then
			WeaponService.give(player, id)
			local data = item.data
			if data and typeof(data.mag) == "number" then
				local _, reserve = WeaponService.getAmmo(player, id)
				local own = typeof(data.reserve) == "number" and not Items.ammoFor(id)
				WeaponService.setAmmo(player, id, data.mag, if own then data.reserve else reserve or 0)
			end
		end
	end
end

local function sync(player: Player)
	local inv = invs[player]
	if not inv then
		return
	end
	syncWeapons(player, inv)
	-- a spare vest in the bag (Client/Vest: V puts it on)
	local spare = nil
	for _, item in allCarried(inv) do
		local def = Items.get(item.id)
		if def and def.Kind == "Armor" then
			spare = item.uid
			break
		end
	end
	player:SetAttribute("SpareArmor", spare)
	StateRemote:FireClient(player, snapshot(inv))
	WeaponService.ammoChanged(player) -- ammo items may have come or gone
end

-- Put count of an item into the containers (stacks first, then empty slots, within weight).
-- Returns how many didn't fit. Doesn't sync.
local function addInto(inv: Inv, id: string, count: number, data: { [string]: any }?): number
	local def = Items.get(id)
	if not def or count <= 0 then
		return count
	end
	local left = count
	for _, name in ORDER do
		local c = CONTAINERS[name]
		local list = (inv :: any)[name]
		if def.Stack > 1 and not data then
			for slot = 1, c.slots do
				local item = list[slot]
				if left > 0 and item and item.id == id and not item.data then
					local n = math.clamp(math.min(def.Stack - item.count, roomByWeight(inv, name, def.Weight)), 0, left)
					item.count += n
					left -= n
				end
			end
		end
		while left > 0 do
			local slot, rot = spotFor(name, list, id)
			if not slot then
				break
			end
			local n = math.min(def.Stack, left, roomByWeight(inv, name, def.Weight))
			if n <= 0 then
				break
			end
			list[slot] = { uid = newUid(), id = id, count = n, rot = if rot then true else nil, data = data }
			left -= n
		end
		if left == 0 then
			break
		end
	end
	return left
end

-- A whole item (keeps its uid/data) into the first container slot it fits. true if placed.
local function placeWhole(inv: Inv, item: Item): boolean
	local w = itemWeight(item)
	for _, name in ORDER do
		local list = (inv :: any)[name]
		local slot, rot = spotFor(name, list, item.id, item.rot)
		if slot and used(inv, name) + w <= maxOf(name) + 1e-6 then
			item.rot = if rot then true else nil
			list[slot] = item
			return true
		end
	end
	return false
end

-- A whole item at a chosen spot: a grid slot (rot = turned) or an empty quick slot, within
-- the weight limit. true if placed.
local function placeAt(inv: Inv, item: Item, to: any, slot: any, rot: any): boolean
	if typeof(slot) ~= "number" or slot % 1 ~= 0 then
		return false
	end
	if to == "Quick" then
		if slot < 1 or slot > QUICK or inv.Quick[slot] or used(inv, to) + itemWeight(item) > maxOf(to) + 1e-6 then
			return false
		end
		item.rot = nil
		inv.Quick[slot] = item
		return true
	end
	local c = typeof(to) == "string" and CONTAINERS[to] or nil
	if not c then
		return false
	end
	local list = (inv :: any)[to]
	local w, h = Grid.baseSize(item.id)
	if rot == true then
		w, h = h, w
	end
	if not Grid.fits(list, c.cols, c.rows, slot, w, h) or used(inv, to) + itemWeight(item) > c.max + 1e-6 then
		return false
	end
	item.rot = if rot == true then true else nil
	list[slot] = item
	return true
end

local function newInventory(player: Player): Inv
	local inv: Inv = { Inventory = {}, Backpack = {}, Quick = {}, Armor = nil }
	local weapons = table.clone(Config.Weapons.DefaultLoadout)
	if RunService:IsStudio() then
		for _, id in Config.Weapons.StudioLoadout do
			table.insert(weapons, id)
		end
	end
	-- guns go in the quick slots first (keys 1-3), each with its starting ammo in the bag
	local q = 1
	for _, id in weapons do
		local wdef = Weapons.get(id) :: any
		if wdef and wdef.Ammo and (wdef.ReserveAmmo or 0) > 0 then
			addInto(inv, wdef.Ammo, wdef.ReserveAmmo)
		end
		if q <= QUICK and Items.get(id) then
			inv.Quick[q] = { uid = newUid(), id = id, count = 1 }
			q += 1
		else
			addInto(inv, id, 1)
		end
	end
	for _, entry in CFG.StartingItems do
		addInto(inv, entry.Id, entry.Count or 1)
	end
	local armorDef = Armor.get(CFG.StartingArmor)
	if armorDef then
		inv.Armor = { uid = newUid(), id = armorDef.Name, count = 1, data = { armor = armorDef.MaxArmor } }
	end
	return inv
end

function InventoryService.get(player: Player): Inv
	local inv = invs[player]
	if not inv then
		inv = newInventory(player)
		invs[player] = inv
		sync(player)
	end
	return inv
end

function InventoryService.add(player: Player, id: string, count: number?, data: { [string]: any }?): number
	local left = addInto(InventoryService.get(player), id, count or 1, data)
	sync(player)
	return left
end

function InventoryService.count(player: Player, id: string): number
	local n = 0
	for _, item in allCarried(InventoryService.get(player)) do
		if item.id == id then
			n += item.count
		end
	end
	return n
end

-- Take up to count of an item out of the bag (smallest stacks first, the quick slots
-- last). Doesn't sync. Returns how many it took.
local function removeFrom(inv: Inv, id: string, count: number): number
	local stacks = {}
	for _, name in { "Backpack", "Inventory", "Quick" } do
		local list = (inv :: any)[name]
		for slot, item in list do
			if item.id == id then
				table.insert(stacks, { list = list, slot = slot, item = item, quick = name == "Quick" })
			end
		end
	end
	table.sort(stacks, function(a, b)
		if a.quick ~= b.quick then
			return not a.quick
		end
		return a.item.count < b.item.count
	end)
	local taken = 0
	for _, st in stacks do
		if taken >= count then
			break
		end
		local n = math.min(st.item.count, count - taken)
		st.item.count -= n
		taken += n
		if st.item.count <= 0 then
			st.list[st.slot] = nil
		end
	end
	return taken
end

function InventoryService.remove(player: Player, id: string, count: number): number
	local inv = invs[player]
	if not inv or count <= 0 then
		return 0
	end
	local taken = removeFrom(inv, id, math.floor(count))
	if taken > 0 then
		sync(player)
	end
	return taken
end

-- guns with Ammo = "<item id>" reload from the bag
WeaponService.setAmmoSource({
	count = function(player: Player, id: string): number
		return if invs[player] then InventoryService.count(player, id) else 0
	end,
	take = function(player: Player, id: string, amount: number): number
		return InventoryService.remove(player, id, amount)
	end,
})

-- The carried item with this uid: list, slot, item.
local function findUid(inv: Inv, uid: string): ({ [number]: Item }?, number?, Item?)
	for _, name in { "Quick", "Inventory", "Backpack" } do
		local list = (inv :: any)[name]
		for slot, item in list do
			if item.uid == uid then
				return list, slot, item
			end
		end
	end
	return nil, nil, nil
end

---------------------------------------------------------------- the ground

local function removeDropped(uid: string)
	local d = dropped[uid]
	if d then
		dropped[uid] = nil
		d.model:Destroy()
	end
end

local pickup -- defined below (the prompt calls it)

local function spawnDropped(item: Item, at: CFrame)
	local def = Items.get(item.id)
	local template = ItemModels.get(item.id)
	local model: Model
	if template then
		model = template:Clone()
	else
		-- no 3D model yet: a small box so it can still be seen and picked up
		model = Instance.new("Model")
		local box = Instance.new("Part")
		box.Size = Vector3.new(0.8, 0.5, 0.8)
		box.Color = Color3.fromRGB(120, 110, 90)
		box.Anchored = true
		box.CanCollide = false
		box.Parent = model
		model.PrimaryPart = box
	end
	model.Name = item.id
	model:SetAttribute("Uid", item.uid)
	model:SetAttribute("ItemId", item.id)
	model:SetAttribute("Count", item.count)
	-- lying on the ground: guns on their side, vests on their back
	local t = def and def.DropTilt or Vector3.zero
	local tilt = CFrame.Angles(math.rad(t.X), math.rad(t.Y), math.rad(t.Z))
	model:PivotTo(at * tilt)
	local cf, size = model:GetBoundingBox()
	model:PivotTo(model:GetPivot() + Vector3.new(0, at.Position.Y - (cf.Position.Y - size.Y / 2), 0))

	local holder = model.PrimaryPart or model:FindFirstChildWhichIsA("BasePart", true)
	if holder then
		local prompt = Instance.new("ProximityPrompt")
		prompt.ActionText = "Pick up"
		prompt.ObjectText = if def then (if item.count > 1 then `{def.Name} x{item.count}` else def.Name) else item.id
		prompt.HoldDuration = 0.25
		prompt.MaxActivationDistance = 8
		prompt.KeyboardKeyCode = Enum.KeyCode.E
		prompt.RequiresLineOfSight = false
		prompt.Parent = holder
		prompt.Triggered:Connect(function(player)
			pickup(player, item.uid, nil, nil)
		end)
	end
	model.Parent = droppedFolder
	dropped[item.uid] = { item = item, model = model, expires = os.clock() + (CFG.DroppedLifetime or 600) }
end

-- where something dropped by this player lands: on the ground a step in front of them
local dropParams = RaycastParams.new()
dropParams.FilterType = Enum.RaycastFilterType.Exclude
local function dropSpot(player: Player): CFrame?
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
	if not root then
		return nil
	end
	dropParams.FilterDescendantsInstances = { character :: Instance, droppedFolder }
	local look = root.CFrame.LookVector
	local spread = Vector3.new(math.random() - 0.5, 0, math.random() - 0.5) * 1.2
	local from = root.Position + Vector3.new(look.X, 0, look.Z).Unit * 2.5 + spread + Vector3.new(0, 2, 0)
	local hit = workspace:Raycast(from, Vector3.new(0, -20, 0), dropParams)
	local ground = if hit then hit.Position else from - Vector3.new(0, 5, 0)
	return CFrame.new(ground) * CFrame.Angles(0, math.random() * math.pi * 2, 0)
end

-- A gun leaving the bag takes the bullets in its magazine with it (and its own spare
-- bullets, for guns without an Ammo item). The live ammo belongs to the weapon, not to one
-- copy: if another copy of the same gun is still carried, this one leaves with what it had
-- stashed (or an empty magazine), so dropping one of two guns can't copy the ammo.
local function stashAmmo(player: Player, item: Item)
	local def = Items.get(item.id)
	if not def or def.Kind ~= "Weapon" then
		return
	end
	local inv = invs[player]
	for _, other in (if inv then allCarried(inv) else {}) do
		if other.id == item.id and other ~= item then
			local data = item.data or {}
			data.mag = if typeof(data.mag) == "number" then data.mag else 0
			if Items.ammoFor(item.id) then
				data.reserve = nil
			end
			item.data = data
			return
		end
	end
	local mag, reserve = WeaponService.getAmmo(player, item.id)
	if mag then
		item.data = { mag = mag, reserve = if Items.ammoFor(item.id) then nil else reserve }
	end
end

local function dropItem(player: Player, item: Item): boolean
	local at = dropSpot(player)
	if not at then
		return false
	end
	stashAmmo(player, item)
	spawnDropped(item, at)
	return true
end

function pickup(player: Player, uid: string, to: string?, toSlot: number?, rot: boolean?)
	local d = dropped[uid]
	local inv = invs[player]
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if not d or not inv or not root or not humanoid or humanoid.Health <= 0 then
		return
	end
	if (root.Position - d.model:GetPivot().Position).Magnitude > CFG.PickupRange then
		return
	end
	local item = d.item
	local def = Items.get(item.id)
	if not def then
		return
	end
	local placed = false
	if to and toSlot and placeAt(inv, item, to, toSlot, rot) then
		placed = true
	elseif item.data or def.Stack <= 1 then
		placed = placeWhole(inv, item)
	else
		local left = addInto(inv, item.id, item.count)
		if left > 0 then
			item.count = left -- the rest stays on the ground
			d.model:SetAttribute("Count", left)
		else
			placed = true
		end
	end
	if placed then
		removeDropped(uid)
	end
	sync(player)
end

---------------------------------------------------------------- moving

-- Move an item so its top-left lands on toSlot (rot: turned 90 degrees), or onto a stack of
-- the same item covering toSlot. Quick slots take one item each (a full one swaps when the
-- other item fits where this one was). Refused if it would overlap something or go over the
-- weight.
local function move(inv: Inv, from: string, fromSlot: number, to: string, toSlot: number, rot: boolean)
	local fromList, toList = (inv :: any)[from], (inv :: any)[to]
	local src: Item? = fromList[fromSlot]
	local def = src and Items.get(src.id)
	if not src or not def then
		return
	end
	local crosses = bucket(from) ~= bucket(to) -- adds weight to the target's limit
	local function stackOnto(dst: Item)
		local room = def.Stack - dst.count
		if crosses then
			room = math.min(room, roomByWeight(inv, to, def.Weight))
		end
		local n = math.clamp(room, 0, src.count)
		dst.count += n
		src.count -= n
		if src.count <= 0 then
			fromList[fromSlot] = nil
		end
	end
	local function stackable(dst: Item?): boolean
		return dst ~= nil and dst ~= src and dst.id == src.id and def.Stack > 1 and not src.data and not dst.data
	end

	if to == "Quick" then
		local dst = toList[toSlot]
		if dst == src then
			return
		end
		if dst and stackable(dst) then
			stackOnto(dst)
			return
		end
		if dst then
			-- swap: the quick slot's item goes where this one was
			if from ~= "Quick" then
				local fc = CONTAINERS[from]
				local occ = Grid.occupancy(fromList, fc.cols)
				local bw, bh = Grid.baseSize(dst.id)
				local dstRot: boolean? = nil
				local fits = Grid.fits(fromList, fc.cols, fc.rows, fromSlot, bw, bh, fromSlot, occ)
				if not fits and bw ~= bh then
					fits = Grid.fits(fromList, fc.cols, fc.rows, fromSlot, bh, bw, fromSlot, occ)
					dstRot = true
				end
				if not fits then
					return
				end
				if crosses then
					local ws, wd = itemWeight(src), itemWeight(dst)
					if
						used(inv, to) - wd + ws > maxOf(to) + 1e-6
						or used(inv, from) - ws + wd > maxOf(from) + 1e-6
					then
						return
					end
				end
				dst.rot = dstRot
			end
			src.rot = nil
			fromList[fromSlot] = dst
			toList[toSlot] = src
			return
		end
		if crosses and used(inv, to) + itemWeight(src) > maxOf(to) + 1e-6 then
			return
		end
		fromList[fromSlot] = nil
		src.rot = nil
		toList[toSlot] = src
		return
	end

	local c = CONTAINERS[to]
	-- same item under the target cell: stack onto it
	local occ = Grid.occupancy(toList, c.cols)
	local underAnchor = occ[toSlot]
	local dst: Item? = if underAnchor then toList[underAnchor] else nil
	if dst and stackable(dst) then
		stackOnto(dst)
		return
	end
	local w, h = Grid.baseSize(src.id)
	if rot then
		w, h = h, w
	end
	if not Grid.fits(toList, c.cols, c.rows, toSlot, w, h, if from == to then fromSlot else nil, occ) then
		return
	end
	if crosses and used(inv, to) + itemWeight(src) > c.max + 1e-6 then
		return
	end
	fromList[fromSlot] = nil
	src.rot = if rot then true else nil
	toList[toSlot] = src
end

local lastMove: { [Player]: number } = {}
MoveRemote.OnServerEvent:Connect(function(player, from, fromKey, to, toKey, rot)
	local inv = invs[player]
	if not inv or typeof(from) ~= "string" or typeof(to) ~= "string" then
		return
	end
	rot = rot == true
	local now = os.clock()
	if now - (lastMove[player] or 0) < 0.05 then
		return
	end
	lastMove[player] = now
	local function validSlot(name: string, key: any): boolean
		local n = if name == "Quick" then QUICK elseif CONTAINERS[name] then CONTAINERS[name].slots else nil
		return n ~= nil and typeof(key) == "number" and key >= 1 and key <= n and key % 1 == 0
	end
	if from == "Ground" then
		if typeof(fromKey) == "string" and to ~= "Ground" then
			local ok = validSlot(to, toKey)
			pickup(player, fromKey, if ok then to else nil, if ok then toKey else nil, rot)
		end
		return
	end
	if not validSlot(from, fromKey) then
		return
	end
	if to == "Ground" then
		local list = (inv :: any)[from]
		local item = list[fromKey]
		if item then
			list[fromKey] = nil
			if not dropItem(player, item) then
				list[fromKey] = item -- no character: keep it
			end
		end
	elseif validSlot(to, toKey) then
		move(inv, from, fromKey, to, toKey, rot)
	end
	sync(player)
end)

RequestRemote.OnServerEvent:Connect(function(player)
	InventoryService.get(player)
	sync(player)
end)

---------------------------------------------------------------- using items (Shared/Items Use)

local using: { [Player]: number } = {} -- player -> token of the use in progress
local useToken = 0

local function notice(player: Player, text: string)
	NoticeRemote:FireClient(player, text)
end

local function stopUsing(player: Player)
	using[player] = nil
	player:SetAttribute("UsingItem", nil)
	player:SetAttribute("UseStart", nil)
	player:SetAttribute("UseEnd", nil)
end

-- who is using: the character and humanoid, if they're up and about
local function usable(player: Player): (Model?, Humanoid?)
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if not character or not humanoid or humanoid.Health <= 0 or character:GetAttribute("Knocked") == true then
		return nil, nil
	end
	return character, humanoid
end

function InventoryService.use(player: Player, uid: string)
	local inv = invs[player]
	local character, humanoid = usable(player)
	if not inv or not character or not humanoid or using[player] then
		return
	end
	local _, _, item = findUid(inv, uid)
	local def = item and Items.get(item.id)
	local action = Items.useAction(def)
	if not item or not def or not def.Use or not action or action.Client then
		return
	end
	local handler = ItemUse[def.Use.Action]
	if not handler then
		warn(`[Inventory] no ItemUse.{def.Use.Action} for {def.Id}`)
		return
	end
	local function ctx()
		return { player = player, character = character, humanoid = humanoid, def = def, use = def.Use }
	end
	if handler.can then
		local ok, why = handler.can(ctx())
		if not ok then
			notice(player, why or `Can't use {def.Name} now`)
			return
		end
	end
	useToken += 1
	local token = useToken
	using[player] = token
	local time = math.max(def.Use.Time or 0, 0)
	local now = workspace:GetServerTimeNow()
	player:SetAttribute("UsingItem", def.Name)
	player:SetAttribute("UseStart", now)
	player:SetAttribute("UseEnd", now + time)
	task.spawn(function()
		local ends = os.clock() + time
		while os.clock() < ends do
			task.wait(0.1)
			if using[player] ~= token then
				return -- cancelled
			end
			local c = usable(player)
			if c ~= character or not invs[player] or not findUid(invs[player], uid) then
				stopUsing(player)
				return
			end
		end
		if using[player] ~= token then
			return
		end
		stopUsing(player)
		local list, slot, still = findUid(inv, uid)
		if not list or not slot or not still or usable(player) ~= character then
			return
		end
		if handler.can then
			local ok, why = handler.can(ctx())
			if not ok then
				notice(player, why or `Can't use {def.Name} now`)
				return
			end
		end
		still.count -= 1
		if still.count <= 0 then
			list[slot] = nil
		end
		handler.apply(ctx())
		sync(player)
	end)
end

UseRemote.OnServerEvent:Connect(function(player, uid)
	if uid == nil then
		if using[player] then
			stopUsing(player)
		end
	elseif typeof(uid) == "string" and #uid <= 64 then
		InventoryService.use(player, uid)
	end
end)

-- An item lying on the ground that anyone can pick up (debug tools, world loot). Returns its uid.
function InventoryService.spawnPickup(id: string, count: number?, at: CFrame, data: { [string]: any }?): string?
	local def = Items.get(id)
	if not def then
		return nil
	end
	local item: Item = { uid = newUid(), id = id, count = math.clamp(math.floor(count or 1), 1, def.Stack), data = data }
	spawnDropped(item, at)
	return item.uid
end

---------------------------------------------------------------- armor (Server/Armor)

function InventoryService.wornArmor(player: Player): Item?
	return InventoryService.get(player).Armor
end

-- Bag -> Armor slot: the vest with this uid, or the first one carried.
function InventoryService.putOnArmor(player: Player, uid: string?): Item?
	local inv = InventoryService.get(player)
	if inv.Armor then
		return nil
	end
	for _, name in { "Quick", "Inventory", "Backpack" } do
		local list = (inv :: any)[name]
		for slot, item in list do
			local def = Items.get(item.id)
			if def and def.Kind == "Armor" and (uid == nil or item.uid == uid) then
				list[slot] = nil
				inv.Armor = item
				sync(player)
				return item
			end
		end
	end
	return nil
end

-- Armor slot -> the bag, keeping the armor points left: at to/slot (rot = turned; to may be
-- "Quick") if it was dragged there and fits, else the first spot, else on the ground.
function InventoryService.takeOffArmor(player: Player, armorLeft: number?, to: any?, slot: any?, rot: any?)
	local inv = InventoryService.get(player)
	local item = inv.Armor
	if not item then
		return
	end
	inv.Armor = nil
	local data: { [string]: any } = item.data or {}
	if typeof(armorLeft) == "number" then
		data.armor = armorLeft
	end
	item.data = data
	local placed = placeAt(inv, item, to, slot, rot)
	if not placed and not placeWhole(inv, item) then
		local at = dropSpot(player)
		if at then
			spawnDropped(item, at)
		else
			inv.Armor = item -- nowhere to put it
		end
	end
	sync(player)
end

-- Refresh the client (Server/Armor calls this when the worn vest changes).
function InventoryService.changed(player: Player)
	sync(player)
end

---------------------------------------------------------------- lifecycle

function InventoryService.start()
	ItemModels.loadAll()
	local function onPlayer(player: Player)
		InventoryService.get(player)
	end
	Players.PlayerAdded:Connect(onPlayer)
	for _, p in Players:GetPlayers() do
		task.spawn(onPlayer, p)
	end
	Players.PlayerRemoving:Connect(function(player)
		invs[player] = nil
		lastMove[player] = nil
		using[player] = nil
	end)
	-- dropped items time out
	task.spawn(function()
		while true do
			task.wait(5)
			local now = os.clock()
			for uid, d in dropped do
				if now > d.expires then
					removeDropped(uid)
				end
			end
		end
	end)
end

return InventoryService
