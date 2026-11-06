--[[
	Server side of the weapon system. Which weapons a player carries follows their inventory
	(Server/Inventory gives / takes them as gun items come and go). The server owns ammo and decides every
	hit; clients only ask ("equip this", "I fired from here toward there").

		WeaponService.give(player, "Pistol")   -- adds it (replaces the weapon in that wheel slot)
		WeaponService.addAmmo(player, "Pistol", 30)  -- spare bullets (guns without an Ammo item), up to MaxReserve
		WeaponService.take(player, "Pistol")
		WeaponService.getAmmo / setAmmo(player, id, mag, reserve)
		WeaponService.inventory(player)        -> { [Slot]: weaponId }
		WeaponService.setAmmoSource(source)    -- Server/Inventory: guns with Ammo = "<item id>"
		                                       -- reload from those items in the bag
		WeaponService.ammoChanged(player)      -- the bag changed: resend the spare-bullet counts

	Spare bullets: a gun with Ammo set (the carbine: "RifleAmmo") has no spare bullets of its
	own; its reserve is how many of that ammo item the player carries, and a reload takes them
	out of the bag. Guns without Ammo keep their own reserve (ReserveAmmo / MaxReserve).

	Remotes (ReplicatedStorage.WeaponRemotes, made here):
		Equip  (client -> server) weaponId | nil
		Fire   (client -> server) direction only; the server picks the origin and checks the
		       direction against the shooter's visible aim (see aimMatches)
		Reload (client -> server)
		Ammo   (server -> owner)  weaponId, mag, reserve
		Shot   (server -> others) shooter, weaponId, origin, hitPositions   -- effects only
		Pose   (client -> server) twist, pitch (radians), aiming, up, plant, lean (-1..1) -> character attributes
		       GunTwist / GunPitch / GunAiming / GunUp / GunPlant / GunLean, so every client can turn that player's waist the same way (Client.Weapons.GunPose)

	The gun model sits in the right hand while equipped and on the back otherwise (GunModel).

	The equipped weapon is also the player attribute "Weapon", so every client can read it.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Weapons = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Weapons"))
local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local Joints = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Joints"))
local Pouches = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Armor"):WaitForChild("Pouches"))
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
type State = {
	bySlot: { [string]: string },
	held: { [string]: Held },
	equipped: string?,
	modelToken: number, -- bumps on every equip so a late holster/draw weld swap is skipped
	readyAt: number, -- os.clock() when the drawn gun is in hand and may fire
}

local states: { [Player]: State } = {}

local function stateOf(player: Player): State
	local s = states[player]
	if not s then
		s = { bySlot = {}, held = {}, equipped = nil, modelToken = 0, readyAt = 0 }
		states[player] = s
	end
	return s
end

export type AmmoSource = {
	count: (player: Player, itemId: string) -> number,
	take: (player: Player, itemId: string, amount: number) -> number, -- returns how many it took
}
local ammoSource: AmmoSource? = nil

function WeaponService.setAmmoSource(source: AmmoSource)
	ammoSource = source
end

-- spare bullets: the ammo items carried, or the gun's own reserve
local function reserveOf(player: Player, id: string, h: Held): number
	local def = Weapons.get(id) :: any
	if def and def.Ammo and ammoSource then
		return ammoSource.count(player, def.Ammo)
	end
	return h.reserve
end

-- take up to amount spare bullets; returns how many it got
local function takeReserve(player: Player, id: string, h: Held, amount: number): number
	local def = Weapons.get(id) :: any
	if def and def.Ammo and ammoSource then
		return ammoSource.take(player, def.Ammo, amount)
	end
	local n = math.min(amount, h.reserve)
	h.reserve -= n
	return n
end

local function sendAmmo(player: Player, id: string)
	local h = stateOf(player).held[id]
	if h then
		AmmoRemote:FireClient(player, id, h.mag, reserveOf(player, id, h))
	end
end

function WeaponService.ammoChanged(player: Player)
	for id in stateOf(player).held do
		sendAmmo(player, id)
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
	s.held[id] = s.held[id]
		or {
			mag = def.MagSize or 0,
			reserve = if (def :: any).Ammo then 0 else def.ReserveAmmo or 0,
			lastFire = 0,
			reloadingUntil = 0,
		}
	player:SetAttribute("Weapons", table.concat(WeaponService.list(player), ","))
	sendAmmo(player, id)
	WeaponService.refreshModel(player)
end

-- Spare bullets for a carried weapon without an Ammo item (pickups, shops), capped at the
-- weapon's MaxReserve. Guns with an Ammo item get it as an item: InventoryService.add.
function WeaponService.addAmmo(player: Player, id: string, amount: number)
	local def = Weapons.get(id)
	local h = stateOf(player).held[id]
	if not def or not h then
		return
	end
	h.reserve = math.clamp(h.reserve + amount, 0, def.MaxReserve or math.huge)
	sendAmmo(player, id)
end

-- Magazine + spare bullets of a carried weapon (the inventory keeps them on a dropped gun, so
-- dropping and picking it up again doesn't refill it).
function WeaponService.getAmmo(player: Player, id: string): (number?, number?)
	local h = stateOf(player).held[id]
	if h then
		return h.mag, reserveOf(player, id, h)
	end
	return nil, nil
end

function WeaponService.setAmmo(player: Player, id: string, mag: number, reserve: number)
	local def = Weapons.get(id)
	local h = stateOf(player).held[id]
	if not def or not h then
		return
	end
	h.mag = math.clamp(math.floor(mag), 0, def.MagSize or 0)
	h.reserve = math.clamp(math.floor(reserve), 0, def.MaxReserve or math.huge)
	sendAmmo(player, id)
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
	WeaponService.refreshModel(player) -- off the back / out of the hand
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
	local old = s.equipped
	s.equipped = id
	player:SetAttribute("Weapon", id)
	s.modelToken += 1
	local token = s.modelToken
	local character = player.Character
	-- putting the gun away or switching cuts a reload short: no refill, the mag goes back in
	local now = os.clock()
	for _, h in s.held do
		if h.reloadingUntil > now then
			h.reloadingUntil = 0
		end
	end
	if character then
		GunModel.cancelReload(character)
	end
	-- holster (Q) / draw from the back: the weld moves when the hand gets there (the clips play
	-- on the client at the same time)
	local swapAt = nil
	if character and id == nil and old and GunModel.inHand(character) then
		swapAt = GunModel.HolsterSwap
	elseif character and id and GunModel.onBack(character, id) then
		swapAt = GunModel.DrawSwap
		s.readyAt = os.clock() + GunModel.DrawLength
	end
	if Config.Weapons.Debug then
		local gun = character and character:FindFirstChild("Gun")
		print(`[Weapons] {player.Name} equip {id} (was {old}); gun on {gun and gun:GetAttribute("On")}; swap in {swapAt or 0}s`)
	end
	if swapAt then
		task.delay(swapAt, function()
			if s.modelToken == token and player.Character == character then
				WeaponService.refreshModel(player)
			elseif Config.Weapons.Debug then
				print(`[Weapons] {player.Name} swap for {id} skipped (newer equip or new character)`)
			end
		end)
	else
		WeaponService.refreshModel(player)
	end
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

PoseRemote.OnServerEvent:Connect(function(player, twist, pitch, aiming, up, plant, lean)
	local character = player.Character
	if not character or typeof(twist) ~= "number" or typeof(pitch) ~= "number" then
		return
	end
	if twist ~= twist or pitch ~= pitch then
		return -- NaN
	end
	character:SetAttribute("GunTwist", math.clamp(twist, -1.6, 1.6))
	character:SetAttribute("GunPitch", math.clamp(pitch, -1.4, 1.4))
	character:SetAttribute("GunAiming", aiming == true)
	character:SetAttribute("GunUp", up == true) -- shouldered: other clients lock the chest to the aim
	character:SetAttribute("GunPlant", plant == true) -- standing aim: feet planted, turn steps
	if typeof(lean) == "number" and lean == lean then
		-- Q / E lean, -1..1 of Config.Weapons.LeanAngle (shots start from the leaned head)
		character:SetAttribute("GunLean", math.clamp(lean, -1, 1))
	end
end)

-- The shot origin: the server's head, tilted round the waist by the shooter's lean (the
-- client leans its chest locally, so the server's copy of the head doesn't move with it).
local function shotOrigin(character: Model, head: BasePart, direction: Vector3): Vector3
	local lean = character:GetAttribute("GunLean")
	local ut = character:FindFirstChild("UpperTorso") :: BasePart?
	local waist = Joints.find(character, "UpperTorso", "Waist") -- Motor6D or AnimationConstraint
	if typeof(lean) ~= "number" or math.abs(lean) < 0.01 or not (ut and waist) then
		return head.Position
	end
	local pivot = (ut :: BasePart).CFrame * Joints.c1(waist)
	local angle = math.rad(Config.Weapons.LeanAngle or 20) * math.clamp(lean, -1, 1)
	local turn = CFrame.fromAxisAngle(direction.Unit, angle)
	local leaned = pivot.Position + turn * (head.Position - pivot.Position)
	-- never through a wall: stop just short of anything between the head and the leaned point
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = { character }
	local step = leaned - head.Position
	local hit = step.Magnitude > 0.01 and workspace:Raycast(head.Position, step, params)
	if hit then
		return head.Position + step.Unit * math.max(0, hit.Distance - 0.1)
	end
	return leaned
end

-- Anti-cheat for shots. The client only says "I fired, toward this direction". The server
-- picks the origin (its own copy of the shooter's head), the spread, the hit and the damage,
-- and the direction must match where the shooter's body visibly aims: chest facing
-- (root + GunTwist) and waist pitch (GunPitch), both replicated to everyone. Silent aim
-- (shooting at someone you're not facing) fails this check and the shot is dropped.
local MAX_YAW_OFF = math.rad(40)
local MAX_PITCH_OFF = math.rad(30)
local RECHECK_AFTER = 0.15 -- facing replicates separately from remotes, so one late recheck

local function aimMatches(character: Model, dir: Vector3): boolean
	local root = character:FindFirstChild("HumanoidRootPart") :: BasePart?
	if not root then
		return false
	end
	local look = root.CFrame.LookVector
	local bodyYaw = math.atan2(-look.X, -look.Z) + (character:GetAttribute("GunTwist") or 0)
	local flat = Vector3.new(dir.X, 0, dir.Z)
	if flat.Magnitude > 0.05 then
		local shotYaw = math.atan2(-flat.X, -flat.Z)
		local d = (shotYaw - bodyYaw + math.pi) % (2 * math.pi) - math.pi
		if math.abs(d) > MAX_YAW_OFF then
			return false
		end
	end
	local pitch = math.asin(math.clamp(dir.Y, -1, 1))
	return math.abs(pitch - (character:GetAttribute("GunPitch") or 0)) <= MAX_PITCH_OFF
end

-- No shooting in the air (jumps, falls); the client already stops it and also blocks rolls.
-- This catches anyone clearly mid-air. The slack covers the shooter's ping right after
-- take-off and just before landing.
local AIR_SLACK = 2.5 -- studs
local groundParams = RaycastParams.new()
groundParams.FilterType = Enum.RaycastFilterType.Exclude
local function airborne(character: Model): boolean
	local root = character:FindFirstChild("HumanoidRootPart") :: BasePart?
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	if not root or not humanoid or humanoid.SeatPart then
		return false
	end
	groundParams.FilterDescendantsInstances = { character }
	local reach = humanoid.HipHeight + root.Size.Y / 2 + AIR_SLACK
	return workspace:Raycast(root.Position, Vector3.new(0, -reach, 0), groundParams) == nil
end

local function flag(player: Player, reason: string)
	local n = (player:GetAttribute("AimFlags") or 0) + 1
	player:SetAttribute("AimFlags", n)
	if n % 10 == 1 then
		warn(`[Weapons] {player.Name} ({player.UserId}) shot rejected: {reason} (x{n})`)
	end
end

local function shoot(player: Player, id: string, def, h: Held, direction: Vector3)
	local character = player.Character
	local head = character and character:FindFirstChild("Head") :: BasePart?
	if not head or stateOf(player).equipped ~= id then
		return
	end
	if def.Class.Kind == "Gun" then
		if h.mag <= 0 then
			return
		end
		h.mag -= 1
	end
	local aiming = character:GetAttribute("GunAiming") == true
	local origin = shotOrigin(character, head, direction)
	local hits = Hitscan.fire(player, def, origin, direction, aiming)
	ShotRemote:FireAllClients(player, id, origin, hits)
	if def.Class.Kind == "Gun" then
		sendAmmo(player, id)
	end
end

FireRemote.OnServerEvent:Connect(function(player, direction)
	if typeof(direction) ~= "Vector3" or direction.Magnitude < 0.01 or direction.Magnitude ~= direction.Magnitude then
		return
	end
	direction = direction.Unit
	local s = stateOf(player)
	local id = s.equipped
	local def = id and Weapons.get(id)
	local h = id and s.held[id]
	local character = player.Character
	if not def or not h or not character or airborne(character) then
		return
	end
	local now = os.clock()
	local interval = 1 / (def.FireRate or 1)
	if now - h.lastFire < interval * 0.8 or now < h.reloadingUntil or now < s.readyAt - 0.1 then
		return -- too fast (some slack for network jitter), reloading or still drawing
	end
	h.lastFire = now
	if def.Class.Kind ~= "Gun" or aimMatches(character, direction) then
		shoot(player, id, def, h, direction)
		return
	end
	task.delay(RECHECK_AFTER, function()
		if player.Character == character and aimMatches(character, direction) then
			shoot(player, id, def, h, direction)
		else
			flag(player, "direction doesn't match where the character aims")
		end
	end)
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
	if need <= 0 or reserveOf(player, id, h) <= 0 or os.clock() < h.reloadingUntil then
		return
	end
	local doneAt = os.clock() + (def.ReloadTime or 1)
	h.reloadingUntil = doneAt
	if player.Character and def.Model then
		GunModel.reloadMag(
			player.Character,
			GunModel.ReloadLength / (def.ReloadTime or GunModel.ReloadLength),
			Pouches.forClass(def.Class)
		)
	end
	task.delay(def.ReloadTime or 1, function()
		if s.held[id] ~= h or h.reloadingUntil ~= doneAt then
			return -- dropped, or cut short by holstering / switching
		end
		h.mag += takeReserve(player, id, h, need)
		sendAmmo(player, id)
	end)
end)

-- load the gun models now, so the first equip / sling doesn't wait for them
for _, def in Weapons.all() do
	if def.Model then
		task.spawn(GunModel.preload, def.Model)
	end
end

Players.PlayerRemoving:Connect(function(player)
	states[player] = nil
end)

-- new character: nothing in hand until the client equips again; the gun goes on the back
local function onPlayer(player: Player)
	player.CharacterAdded:Connect(function(character)
		local s = stateOf(player)
		s.equipped = nil
		s.modelToken += 1
		s.readyAt = 0
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
