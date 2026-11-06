--[[
	Movement checks (Config.AntiCheat). Every player's client moves their own character, so a
	cheat can speed it up or teleport it. Every CheckEvery seconds the server compares where
	each character is with where it was:
	  - on foot: further than TeleportStuds in one window, or faster than MaxFootSpeed for
	    Strikes windows in a row -> pulled back to the last good spot;
	  - knocked down: the body may only slide KnockedDrift studs from where it fell;
	  - in a seat: skipped here (Server/Vehicles checks the car).
	Falling is free (only horizontal movement counts). The server's own moves (spawning,
	getting out of a car) call Guard.allowTeleport first, which skips the next check.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local Guard = require(script.Parent:WaitForChild("Guard"))

local function cfg()
	return Config.AntiCheat or {}
end

-- last = where it was at the previous check, good = the last spot that passed
type Track = { character: Model, last: Vector3, good: Vector3, strikes: number, knockedAt: Vector3? }
local tracks: { [Player]: Track } = {}

local function flat(v: Vector3): Vector3
	return Vector3.new(v.X, 0, v.Z)
end

local function pullBack(character: Model, root: BasePart, to: Vector3)
	-- keep the facing, move back, stop the fling
	local cf = root.CFrame
	character:PivotTo(CFrame.new(to) * cf.Rotation)
	root.AssemblyLinearVelocity = Vector3.zero
end

-- standing on a car (riding on the roof moves you at car speed)
local floorParams = RaycastParams.new()
floorParams.FilterType = Enum.RaycastFilterType.Exclude
local function onVehicle(character: Model, root: BasePart): boolean
	local cars = workspace:FindFirstChild("Vehicles")
	if not cars then
		return false
	end
	floorParams.FilterDescendantsInstances = { character }
	local hit = workspace:Raycast(root.Position, Vector3.new(0, -8, 0), floorParams)
	return hit ~= nil and hit.Instance:IsDescendantOf(cars)
end

local function onCharacter(player: Player, character: Model)
	Guard.allowTeleport(player)
	local root = character:WaitForChild("HumanoidRootPart", 10) :: BasePart?
	if root and player.Character == character then
		tracks[player] = { character = character, last = root.Position, good = root.Position, strikes = 0 }
	end
end

local function onPlayer(player: Player)
	player.CharacterAdded:Connect(function(character)
		onCharacter(player, character)
	end)
	if player.Character then
		task.spawn(onCharacter, player, player.Character)
	end
end

local function check(player: Player, t: Track, window: number)
	local c = cfg()
	local character = t.character
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	local root = character:FindFirstChild("HumanoidRootPart") :: BasePart?
	if player.Character ~= character or not humanoid or not root then
		return
	end
	local pos = root.Position

	-- server teleports, seats (cars check themselves), standing on a car, real deaths: just follow
	if
		Guard.teleportAllowed(player)
		or humanoid.SeatPart
		or onVehicle(character, root)
		or humanoid:GetState() == Enum.HumanoidStateType.Dead
	then
		t.last, t.good, t.strikes, t.knockedAt = pos, pos, 0, nil
		return
	end

	if character:GetAttribute("Knocked") == true then
		t.knockedAt = t.knockedAt or t.good
		local drift = flat(pos - t.knockedAt).Magnitude
		if drift > (c.KnockedDrift or 12) then
			Guard.flag(player, "moved while knocked down")
			pullBack(character, root, t.knockedAt + Vector3.new(0, 1, 0))
			pos = t.knockedAt
		end
		t.last, t.good, t.strikes = pos, pos, 0
		return
	end
	t.knockedAt = nil

	local moved = flat(pos - t.last).Magnitude
	if moved > (c.TeleportStuds or 80) then
		Guard.flag(player, `teleported {math.floor(moved)} studs`)
		pullBack(character, root, t.good)
		t.last, t.strikes = t.good, 0
		return
	end
	if moved / window > (c.MaxFootSpeed or 45) then
		t.strikes += 1
		t.last = pos
		if t.strikes >= (c.Strikes or 2) then
			Guard.flag(player, `too fast ({math.floor(moved / window)} studs/s)`)
			pullBack(character, root, t.good)
			t.last, t.strikes = t.good, 0
		end
		return -- a single fast window (a car bump) is let go; good stays where it was
	end
	t.strikes = 0
	t.last, t.good = pos, pos
end

Players.PlayerAdded:Connect(onPlayer)
for _, p in Players:GetPlayers() do
	onPlayer(p)
end
Players.PlayerRemoving:Connect(function(player)
	tracks[player] = nil
end)

task.spawn(function()
	local lastAt = os.clock()
	while true do
		task.wait(cfg().CheckEvery or 0.5)
		local now = os.clock()
		local window = math.max(0.05, now - lastAt)
		lastAt = now
		for player, t in tracks do
			local ok, err = pcall(check, player, t, window)
			if not ok then
				warn("[MovementGuard]", err)
			end
		end
	end
end)
