--[[
	Server side of the weapon system. The server owns inventories and ammo and decides every
	hit; clients only ask ("equip this", "I fired from here toward there").

		WeaponService.give(player, "Pistol")   -- adds it (replaces the weapon in that wheel slot)
		WeaponService.take(player, "Pistol")
		WeaponService.inventory(player)        -> { [Slot]: weaponId }

	Remotes (ReplicatedStorage.WeaponRemotes, made here):
		Equip  (client -> server) weaponId | nil
		Fire   (client -> server) origin, direction, aiming
		Reload (client -> server)
		Ammo   (server -> owner)  weaponId, mag, reserve
		Shot   (server -> others) shooter, weaponId, origin, hitPositions   -- effects only
		Pose   (client -> server) twist, pitch (radians) -> character attributes GunTwist /
		       GunPitch, so every client can turn that player's waist the same way (Client.Weapons.GunPose)

	The gun model sits in the right hand while equipped and on the back otherwise (GunModel).

	The equipped weapon is also the player attribute "Weapon", so every client can read it.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Weapons = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Weapons"))
local Hitscan = require(script.Parent:WaitForChild("Hitscan"))
local GunModel = require(script.Parent:WaitForChild("GunModel"))

local WeaponService = {}

local remotes = Instance.new("Folder")
remotes.Name = "WeaponRemotes"
local function remote(name: string): RemoteEvent
	local r = Instance.new("RemoteEvent")
	r.Name = name
	r.Parent = remotes
	return r
end
local EquipRemote = remote("Equip")
local FireRemote = remote("Fire")
local ReloadRemote = remote("Reload")
local AmmoRemote = remote("Ammo")
local ShotRemote = remote("Shot")
local PoseRemote = remote("Pose")
remotes.Parent = ReplicatedStorage

type Held = { mag: number, reserve: number, lastFire: number, reloadingUntil: number }
type State = { bySlot: { [string]: string }, held: { [string]: Held }, equipped: string? }

local states: { [Player]: State } = {}

local function stateOf(player: Player): State
	local s = states[player]
	if not s then
		s = { bySlot = {}, held = {}, equipped = nil }
		states[player] = s
	end
	return s
end

local function sendAmmo(player: Player, id: string)
	local h = stateOf(player).held[id]
	if h then
		AmmoRemote:FireClient(player, id, h.mag, h.reserve)
	end
end

function WeaponService.give(player: Player, id: string)
	local def = Weapons.get(id)
	assert(def, `unknown weapon {id}`)
	local s = stateOf(player)
	local slot = def.Class.Slot
	local old = s.bySlot[slot]
	if old and old ~= id then
		WeaponService.take(player, old)
	end
	s.bySlot[slot] = id
	s.held[id] = s.held[id] or { mag = def.MagSize or 0, reserve = def.ReserveAmmo or 0, lastFire = 0, reloadingUntil = 0 }
	player:SetAttribute("Weapons", table.concat(WeaponService.list(player), ","))
	sendAmmo(player, id)
	WeaponService.refreshModel(player)
end

function WeaponService.take(player: Player, id: string)
	local s = stateOf(player)
	for slot, held in s.bySlot do
		if held == id then
			s.bySlot[slot] = nil
		end
	end
	s.held[id] = nil
	if s.equipped == id then
		s.equipped = nil
		player:SetAttribute("Weapon", nil)
	end
	player:SetAttribute("Weapons", table.concat(WeaponService.list(player), ","))
end

function WeaponService.list(player: Player): { string }
	local out = {}
	for _, id in stateOf(player).bySlot do
		table.insert(out, id)
	end
	table.sort(out)
	return out
end

function WeaponService.inventory(player: Player): { [string]: string }
	return table.clone(stateOf(player).bySlot)
end

EquipRemote.OnServerEvent:Connect(function(player, id)
	local s = stateOf(player)
	if id ~= nil and (typeof(id) ~= "string" or not s.held[id]) then
		return
	end
	s.equipped = id
	player:SetAttribute("Weapon", id)
	WeaponService.refreshModel(player)
end)

-- Gun in hand when equipped, otherwise the first carried gun with a model goes on the back.
function WeaponService.refreshModel(player: Player)
	local character = player.Character
	if not character then
		return
	end
	local s = stateOf(player)
	local def = s.equipped and Weapons.get(s.equipped)
	if def and def.Model then
		GunModel.hold(character, def)
		return
	end
	for _, id in WeaponService.list(player) do
		local d = Weapons.get(id)
		if d and d.Model then
			GunModel.sling(character, d)
			return
		end
	end
	GunModel.remove(character)
end

PoseRemote.OnServerEvent:Connect(function(player, twist, pitch)
	local character = player.Character
	if not character or typeof(twist) ~= "number" or typeof(pitch) ~= "number" then
		return
	end
	if twist ~= twist or pitch ~= pitch then
		return -- NaN
	end
	character:SetAttribute("GunTwist", math.clamp(twist, -1.6, 1.6))
	character:SetAttribute("GunPitch", math.clamp(pitch, -1.4, 1.4))
end)

FireRemote.OnServerEvent:Connect(function(player, origin, direction, aiming)
	if typeof(origin) ~= "Vector3" or typeof(direction) ~= "Vector3" then
		return
	end
	local s = stateOf(player)
	local id = s.equipped
	local def = id and Weapons.get(id)
	local h = id and s.held[id]
	if not def or not h then
		return
	end
	local now = os.clock()
	local interval = 1 / (def.FireRate or 1)
	if now - h.lastFire < interval * 0.8 or now < h.reloadingUntil then
		return -- too fast (some slack for network jitter) or reloading
	end
	if def.Class.Kind == "Gun" then
		if h.mag <= 0 then
			return
		end
		h.mag -= 1
	end
	h.lastFire = now

	local hits = Hitscan.fire(player, def, origin, direction, aiming == true)
	ShotRemote:FireAllClients(player, id, origin, hits)
	if def.Class.Kind == "Gun" then
		sendAmmo(player, id)
	end
end)

ReloadRemote.OnServerEvent:Connect(function(player)
	local s = stateOf(player)
	local id = s.equipped
	local def = id and Weapons.get(id)
	local h = id and s.held[id]
	if not def or not h or def.Class.Kind ~= "Gun" then
		return
	end
	local need = (def.MagSize or 0) - h.mag
	if need <= 0 or h.reserve <= 0 or os.clock() < h.reloadingUntil then
		return
	end
	h.reloadingUntil = os.clock() + (def.ReloadTime or 1)
	task.delay(def.ReloadTime or 1, function()
		if s.held[id] ~= h then
			return
		end
		local take = math.min(need, h.reserve)
		h.mag += take
		h.reserve -= take
		sendAmmo(player, id)
	end)
end)

Players.PlayerRemoving:Connect(function(player)
	states[player] = nil
end)

-- new character: nothing in hand until the client equips again; the gun goes on the back
local function onPlayer(player: Player)
	player.CharacterAdded:Connect(function(character)
		stateOf(player).equipped = nil
		player:SetAttribute("Weapon", nil)
		character:WaitForChild("UpperTorso", 10)
		WeaponService.refreshModel(player)
	end)
end
Players.PlayerAdded:Connect(onPlayer)
for _, p in Players:GetPlayers() do
	onPlayer(p)
end

return WeaponService
