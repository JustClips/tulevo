--[[
	Debug panel, server side (the window is Client/DebugPanel.client.luau, F8).

	Only Config.Debug.Admins (and anyone in Studio play tests when AllowInStudio is on) may use
	it. The server sets the Player attribute "DebugAdmin" so the client knows to build the
	window, but every action below checks the account again, so a faked attribute does nothing.

	One RemoteFunction, ReplicatedStorage.DebugRemotes.Run(action, a, b) -> (ok, message).
	Everything acts on the admin's own character only.

	Weather: if a Server/Weather module shows up (list() -> { string }, set(name)) the panel
	uses it. Until then there are three simple Lighting looks (Clear, Overcast, Fog).
]]

local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local GameTime = require(Shared:WaitForChild("GameTime"))
local Items = require(Shared:WaitForChild("Items"))
local Vehicles = require(Shared:WaitForChild("Vehicles"))
local Weapons = require(Shared:WaitForChild("Weapons"))

local Server = script.Parent
local Money = require(Server:WaitForChild("Money"))
local Damage = require(Server:WaitForChild("Damage"))
local Knocked = require(Server:WaitForChild("Knocked"))
local InventoryService = require(Server:WaitForChild("Inventory"):WaitForChild("InventoryService"))
local VehicleService = require(Server:WaitForChild("Vehicles"):WaitForChild("VehicleService"))
local Guard = require(Server:WaitForChild("Guard"))
local WeaponService = require(Server:WaitForChild("Weapons"):WaitForChild("WeaponService"))

local cfg = Config.Debug or {}

local remotes = Instance.new("Folder")
remotes.Name = "DebugRemotes"
local Run = Instance.new("RemoteFunction")
Run.Name = "Run"
Run.Parent = remotes
remotes.Parent = ReplicatedStorage

local function isAdmin(player: Player): boolean
	if cfg.AllowInStudio and RunService:IsStudio() then
		return true
	end
	return table.find(cfg.Admins or {}, player.UserId) ~= nil
end

---------------------------------------------------------------- helpers

local function parts(player: Player): (Model?, Humanoid?, BasePart?)
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	local root = character and character:FindFirstChild("HumanoidRootPart")
	return character, humanoid, root :: BasePart?
end

local function groundBelow(x: number, z: number, ignore: { Instance }): Vector3?
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = ignore
	params.RespectCanCollide = true
	local hit = workspace:Raycast(Vector3.new(x, 2000, z), Vector3.new(0, -4000, 0), params)
	return hit and hit.Position
end

local function int(v: any, lo: number, hi: number): number?
	local n = tonumber(v)
	if not n or n ~= n then
		return nil
	end
	return math.clamp(math.floor(n + 0.5), lo, hi)
end

---------------------------------------------------------------- weather

local Weather = Server:FindFirstChild("Weather")
local weatherModule = nil
if Weather and Weather:IsA("ModuleScript") then
	local ok, mod = pcall(require, Weather)
	if ok and type(mod) == "table" and type(mod.set) == "function" then
		weatherModule = mod
	end
end

local atmosphere = Lighting:FindFirstChildOfClass("Atmosphere")
local base = {
	Brightness = Lighting.Brightness,
	FogEnd = Lighting.FogEnd,
	FogColor = Lighting.FogColor,
	Density = atmosphere and atmosphere.Density,
	Haze = atmosphere and atmosphere.Haze,
	AtmoColor = atmosphere and atmosphere.Color,
}

local LOOKS = {
	Clear = {},
	Overcast = { Brightness = 0.55, Density = 0.42, Haze = 2.2, Color = Color3.fromRGB(170, 175, 182) },
	Fog = { Brightness = 0.7, Density = 0.62, Haze = 3, Color = Color3.fromRGB(190, 195, 200), FogEnd = 350 },
}
local LOOK_ORDER = { "Clear", "Overcast", "Fog" }

local function weatherList(): { string }
	if weatherModule and type(weatherModule.list) == "function" then
		local ok, list = pcall(weatherModule.list)
		if ok and type(list) == "table" then
			list = table.clone(list)
			if type(weatherModule.auto) == "function" then
				table.insert(list, "Auto") -- back to the random cycle
			end
			return list
		end
	end
	return LOOK_ORDER
end

local function setWeather(name: string): (boolean, string)
	if weatherModule then
		if name == "Auto" and type(weatherModule.auto) == "function" then
			weatherModule.auto()
			return true, "Weather: automatic cycle"
		end
		if type(weatherModule.list) == "function" and not table.find(weatherModule.list(), name) then
			return false, "Unknown weather"
		end
		local ok, err = pcall(weatherModule.set, name)
		return ok, if ok then `Weather: {name}` else `Weather failed: {err}`
	end
	local look = LOOKS[name]
	if not look then
		return false, "Unknown weather"
	end
	if not atmosphere then
		atmosphere = Instance.new("Atmosphere")
		atmosphere.Parent = Lighting
		base.Density, base.Haze, base.AtmoColor = atmosphere.Density, atmosphere.Haze, atmosphere.Color
	end
	Lighting.Brightness = base.Brightness * (look.Brightness or 1)
	Lighting.FogEnd = look.FogEnd or base.FogEnd
	atmosphere.Density = look.Density or base.Density
	atmosphere.Haze = look.Haze or base.Haze
	atmosphere.Color = look.Color or base.AtmoColor
	return true, `Weather: {name}`
end

---------------------------------------------------------------- cars

local spawned: { [Player]: { Model } } = {}
local MAX_CARS = 3 -- per admin; the oldest goes when a 4th is spawned

local function spawnCar(player: Player, id: any): (boolean, string)
	local def = type(id) == "string" and Vehicles.get(id)
	local character, humanoid, root = parts(player)
	if not def then
		return false, "Unknown car"
	end
	if not root or not humanoid then
		return false, "No character"
	end
	local look = root.CFrame.LookVector * Vector3.new(1, 0, 1)
	look = if look.Magnitude > 0.01 then look.Unit else Vector3.new(0, 0, -1)
	local at = root.Position + look * 14
	local ground = groundBelow(at.X, at.Z, { character :: Model })
	local groundY = if ground then ground.Y else root.Position.Y - 3
	local height = def.Wheels.Radius + def.Suspension.Length * 0.5 - def.Wheels.FL.Y + 0.5
	local pos = Vector3.new(at.X, groundY + height, at.Z)
	-- side-on to the player, so you walk up to the driver's door
	local cf = CFrame.lookAt(pos, pos + Vector3.new(-look.Z, 0, look.X))
	local ok, model = pcall(VehicleService.spawn, def.Id, cf)
	if not ok then
		return false, `Spawn failed: {model}`
	end
	local list = spawned[player] or {}
	spawned[player] = list
	table.insert(list, model)
	while #list > MAX_CARS do
		local old = table.remove(list, 1)
		if old and old.Parent then
			VehicleService.despawn(old)
		end
	end
	return true, `Spawned {def.Name or def.Id}`
end

local function clearCars(player: Player): (boolean, string)
	local n = 0
	for _, model in spawned[player] or {} do
		if model.Parent then
			VehicleService.despawn(model)
			n += 1
		end
	end
	spawned[player] = nil
	return true, `Removed {n} car(s)`
end

---------------------------------------------------------------- god mode

local function applyGod(player: Player)
	local character = player.Character
	if not character then
		return
	end
	local ff = character:FindFirstChild("DebugGod")
	if player:GetAttribute("DebugGod") then
		if not ff then
			ff = Instance.new("ForceField")
			ff.Name = "DebugGod"
			ff.Visible = false
			ff.Parent = character
		end
	elseif ff then
		ff:Destroy()
	end
end

---------------------------------------------------------------- actions

local actions: { [string]: (Player, any, any) -> (boolean, string) } = {}

function actions.GiveItem(player, id, count)
	local def = type(id) == "string" and Items.get(id)
	if not def then
		return false, "Unknown item"
	end
	local n = int(count, 1, 99) or 1
	local left = InventoryService.add(player, def.Id, n)
	if left >= n then
		return false, `No room for {def.Name}`
	elseif left > 0 then
		return true, `Gave {n - left} {def.Name} (no room for {left})`
	end
	return true, `Gave {n} {def.Name}`
end

function actions.FillAmmo(player)
	local n = 0
	for _, id in WeaponService.list(player) do
		local def = Weapons.get(id)
		if def then
			WeaponService.setAmmo(player, id, def.MagSize or 0, def.MaxReserve or def.ReserveAmmo or 0)
			-- guns that reload from an ammo item (Items/Defs): top the bag up to ReserveAmmo
			local ammo = (def :: any).Ammo
			if ammo then
				local want = (def.ReserveAmmo or 0) - InventoryService.count(player, ammo)
				if want > 0 then
					InventoryService.add(player, ammo, want)
				end
			end
			n += 1
		end
	end
	return true, `Filled ammo on {n} weapon(s)`
end

function actions.AddMoney(player, which, amount)
	local n = int(amount, -1e9, 1e9)
	if not n or (which ~= "Cash" and which ~= "Bank") then
		return false, "Bad amount"
	end
	local ok = if which == "Cash" then Money.addCash(player, n) else Money.addBank(player, n)
	if not ok then
		return false, `Not enough {which}`
	end
	return true, `{which} {if n >= 0 then "+" else ""}{n}`
end

function actions.SetMoney(player, which, amount)
	local n = int(amount, 0, 1e9)
	if not n or (which ~= "Cash" and which ~= "Bank") then
		return false, "Bad amount"
	end
	local cash, bank = Money.get(player)
	local diff = n - (if which == "Cash" then cash else bank)
	if which == "Cash" then
		Money.addCash(player, diff)
	else
		Money.addBank(player, diff)
	end
	return true, `{which} set to {n}`
end

function actions.SetTime(_player, hour, minute)
	local h = int(hour, 0, 23)
	local m = int(minute, 0, 59) or 0
	local total = GameTime.totalMinutes()
	if not h or not total then
		return false, "Clock not running"
	end
	local dayStart = math.floor(total / 1440) * 1440
	local target = dayStart + h * 60 + m
	if target < total then
		target += 1440 -- always forward, so the date never goes back
	end
	Shared:SetAttribute("ClockOriginMinutes", target)
	Shared:SetAttribute("ClockOrigin", workspace:GetServerTimeNow())
	return true, string.format("Time set to %02d:%02d", h, m)
end

function actions.Weather(_player, name)
	if type(name) ~= "string" then
		return false, "Unknown weather"
	end
	return setWeather(name)
end

function actions.Lightning(player)
	local mod = Server:FindFirstChild("Lightning")
	if not mod then
		return false, "No lightning module"
	end
	return require(mod :: ModuleScript).strikeNear(player)
end

function actions.SpawnCar(player, id)
	return spawnCar(player, id)
end

function actions.ClearCars(player)
	return clearCars(player)
end

function actions.Knock(player)
	local character, humanoid = parts(player)
	if not humanoid or not character then
		return false, "No character"
	end
	if Knocked.isKnocked(character) then
		return false, "Already knocked down"
	end
	if player:GetAttribute("DebugGod") then
		player:SetAttribute("DebugGod", nil) -- otherwise nothing could hurt you afterwards either
		applyGod(player)
	end
	humanoid.Health = 0 -- Knocked sees 0 and ragdolls
	return true, "Knocked down"
end

function actions.Revive(player)
	local character, humanoid = parts(player)
	if not humanoid or not character then
		return false, "No character"
	end
	if not Knocked.isKnocked(character) then
		return false, "Not knocked down"
	end
	Knocked.revive(character, humanoid.MaxHealth)
	return true, "Revived"
end

function actions.Heal(player)
	local character, humanoid = parts(player)
	if not humanoid or not character then
		return false, "No character"
	end
	if Knocked.isKnocked(character) then
		Knocked.revive(character, humanoid.MaxHealth)
	end
	humanoid.Health = humanoid.MaxHealth
	local _, maxArmor = Damage.getArmor(humanoid)
	if maxArmor > 0 then
		Damage.addArmor(humanoid, maxArmor)
	end
	return true, "Health and armor full"
end

function actions.God(player)
	local on = not player:GetAttribute("DebugGod")
	player:SetAttribute("DebugGod", if on then true else nil)
	applyGod(player)
	return true, if on then "God mode on" else "God mode off"
end

local function teleportTo(player: Player, pos: Vector3): (boolean, string)
	local character, humanoid, root = parts(player)
	if not character or not humanoid or not root then
		return false, "No character"
	end
	if humanoid.SeatPart then
		return false, "Get out of the car first"
	end
	if Knocked.isKnocked(character) then
		return false, "Knocked down"
	end
	local flatLook = root.CFrame.LookVector * Vector3.new(1, 0, 1)
	local up = humanoid.HipHeight + root.Size.Y / 2 + 0.5
	local at = pos + Vector3.new(0, up, 0)
	Guard.allowTeleport(player, 1) -- else MovementGuard pulls them back
	character:PivotTo(if flatLook.Magnitude > 0.01 then CFrame.lookAt(at, at + flatLook) else CFrame.new(at))
	root.AssemblyLinearVelocity = Vector3.zero
	return true, string.format("Teleported to %d, %d, %d", pos.X, pos.Y, pos.Z)
end

-- a point picked on the map / in the world: X and Z count, the ground below decides Y
function actions.TeleportXZ(player, x, z)
	local px, pz = tonumber(x), tonumber(z)
	if not px or not pz or px ~= px or pz ~= pz or math.abs(px) > 1e5 or math.abs(pz) > 1e5 then
		return false, "Bad position"
	end
	local ground = groundBelow(px, pz, { player.Character :: Model })
	if not ground then
		return false, "No ground there"
	end
	return teleportTo(player, ground)
end

-- an exact point (clicked in the world): land on whatever is just below it
function actions.TeleportPoint(player, pos)
	if typeof(pos) ~= "Vector3" or pos.Magnitude > 1e5 or pos.X ~= pos.X then
		return false, "Bad position"
	end
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = { player.Character :: Model }
	params.RespectCanCollide = true
	local hit = workspace:Raycast(pos + Vector3.new(0, 3, 0), Vector3.new(0, -50, 0), params)
	return teleportTo(player, if hit then hit.Position else pos)
end

function actions.TeleportSpawn(player)
	local spawnPart = workspace:FindFirstChild("Spawn", true)
	if not spawnPart or not spawnPart:IsA("BasePart") then
		return false, "No Spawn part"
	end
	return teleportTo(player, spawnPart.Position + Vector3.new(0, spawnPart.Size.Y / 2, 0))
end

function actions.TeleportToPlayer(player, userId)
	local other = Players:GetPlayerByUserId(tonumber(userId) or 0)
	if not other or other == player then
		return false, "Player not found"
	end
	local _, _, root = parts(other)
	if not root then
		return false, "Player not found"
	end
	return teleportTo(player, root.Position - Vector3.new(0, 2.5, 0) + root.CFrame.RightVector * 4)
end

-- lists for the window: items, cars, weathers
function actions.Info(_player)
	local items = {}
	for _, def in Items.all() do
		table.insert(items, { Id = def.Id, Name = def.Name, Kind = def.Kind })
	end
	local cars = {}
	for _, def in Vehicles.all() do
		table.insert(cars, { Id = def.Id, Name = def.Name or def.Id })
	end
	table.sort(cars, function(a, b)
		return a.Name < b.Name
	end)
	return true, { items = items, cars = cars, weathers = weatherList() } :: any
end

Run.OnServerInvoke = function(player, action, a, b)
	if not isAdmin(player) then
		return false, "Not allowed"
	end
	local fn = type(action) == "string" and actions[action]
	if not fn then
		return false, "Unknown action"
	end
	local ok, success, message = pcall(fn, player, a, b)
	if not ok then
		warn("[DebugPanel]", action, success)
		return false, "Error: " .. tostring(success)
	end
	return success, message
end

---------------------------------------------------------------- players

local function onPlayer(player: Player)
	if isAdmin(player) then
		player:SetAttribute("DebugAdmin", true)
	end
	player.CharacterAdded:Connect(function()
		task.defer(applyGod, player)
	end)
end

Players.PlayerAdded:Connect(onPlayer)
for _, p in Players:GetPlayers() do
	task.spawn(onPlayer, p)
end
Players.PlayerRemoving:Connect(function(player)
	clearCars(player)
end)
