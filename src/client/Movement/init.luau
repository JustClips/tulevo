--[[
	Movement: the on-foot move system for the local character.

	Every move is a module in Movement/Moves. Each frame the controller asks the moves which
	ones want to run and picks the one with the highest Priority. The active move sets the
	target WalkSpeed and can run its own code. Walking, jogging and sprinting share one foot
	animation layer (Movement/Gait) that blends the clips by real speed so feet stay planted
	(up to each gait's calm top cadence; past that the feet slide a little rather than spin).

	Moves: Walk 0, Crouch 5, Sprint 10, SprintStop 11 (let go mid-sprint: skid), Pivot 11
	(reverse while running: plant and turn), Aim 12, Air 20, Roll 30. Footwork clips come from
	art/anim/steps.py.

	Adding a move (crouch, dive, roll, ...): copy Moves/Sprint.luau, give it a Priority, and
	add an input in Movement/Input.luau if it needs one. A move that plays its own animation
	sets UsesGait = false so the foot layer fades out while it runs.

	Move fields:
		Name: string
		Priority: number                        -- highest active move wins (Walk = 0)
		CanStart: (ctx) -> boolean               -- may this move begin now?
		KeepGoing: ((ctx) -> boolean)?           -- may it continue? (default: CanStart)
		Speed: ((ctx) -> number)?                -- target WalkSpeed while active
		UsesGait: boolean?                       -- false = the walk/run layer fades out
		Start / Stop: ((ctx) -> ())?
		Update: ((ctx, dt) -> ())?

	ctx (shared by all moves): Player, Character, Humanoid, Root, Animator, Input, Config,
	Speed (horizontal studs/s), Grounded, Wants (stick/WASD pushed), Active (move name), JumpedAt,
	LoadClip(name) -> AnimationTrack (ids from Shared.AnimIds).
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local AnimIds = require(Shared:WaitForChild("AnimIds"))
local Input = require(script:WaitForChild("Input"))
local Gait = require(script:WaitForChild("Gait"))
local FirstPersonCamera = require(script:WaitForChild("FirstPersonCamera"))

local Movement = {}

local moves = {}
for _, m in script:WaitForChild("Moves"):GetChildren() do
	if m:IsA("ModuleScript") then
		table.insert(moves, require(m))
	end
end
table.sort(moves, function(a, b)
	return a.Priority > b.Priority
end)

local GROUND_STATES = {
	[Enum.HumanoidStateType.Running] = true,
	[Enum.HumanoidStateType.RunningNoPhysics] = true,
	[Enum.HumanoidStateType.Landed] = true,
}

local connection: RBXScriptConnection? = nil
local jumpConnection: RBXScriptConnection? = nil
local current = nil -- the active move
local ctx = nil
local preparing = false -- jump wind-up until just after take-off

-- Jump events for other systems (the gun arms follow the jump):
--   Movement.on(function(event, ...) end)
--   "Prep" (kind, seconds until take-off), "TakeOff" (kind), "Land" (moving)
local listeners: { (string, ...any) -> () } = {}
function Movement.on(fn: (string, ...any) -> ())
	table.insert(listeners, fn)
end
local function emit(event: string, ...)
	for _, fn in listeners do
		task.spawn(fn, event, ...)
	end
end

function Movement.active(): string?
	return current and current.Name
end

-- Rolling, winding up a jump, or in the air (no shooting then, like GTA).
function Movement.busy(): boolean
	if preparing then
		return true
	end
	local name = current and current.Name
	if name == "Roll" or name == "Air" then
		return true
	end
	local st = ctx and ctx.Humanoid and ctx.Humanoid:GetState()
	return st == Enum.HumanoidStateType.Jumping or st == Enum.HumanoidStateType.Freefall
end

local function setMove(move)
	if move == current then
		return
	end
	if current and current.Stop then
		current.Stop(ctx)
	end
	current = move
	ctx.Active = move.Name
	if move.Start then
		move.Start(ctx)
	end
end

local function bind(character: Model)
	if connection then
		connection:Disconnect()
		connection = nil
	end
	if jumpConnection then
		jumpConnection:Disconnect()
		jumpConnection = nil
	end
	if current and ctx and current.Stop then
		current.Stop(ctx)
	end
	current = nil

	local humanoid = character:WaitForChild("Humanoid") :: Humanoid
	local root = character:WaitForChild("HumanoidRootPart") :: BasePart
	if humanoid.RigType ~= Enum.HumanoidRigType.R15 then
		return
	end
	local animator = humanoid:WaitForChild("Animator") :: Animator

	ctx = {
		Player = Players.LocalPlayer,
		Character = character,
		Humanoid = humanoid,
		Root = root,
		Animator = animator,
		Input = Input,
		Config = Config,
		Speed = 0,
		Grounded = true,
		Wants = false,
		Active = nil,
	}
	function ctx.LoadClip(name: string): AnimationTrack
		local anim = Instance.new("Animation")
		anim.AnimationId = assert(AnimIds[name], `no animation id for {name}`)
		return animator:LoadAnimation(anim)
	end

	ctx.JumpedAt = 0 -- os.clock() of the last jump, for Moves/Air
	ctx.JumpKind = "Move" -- "Stand" | "Move" | "Sprint", picked from speed at take-off
	ctx.Emit = emit
	humanoid.StateChanged:Connect(function(_, new)
		if new == Enum.HumanoidStateType.Jumping then
			ctx.JumpedAt = os.clock()
		end
	end)

	-- Jumps go through here so every jump winds up first: both knees dip, then both feet push
	-- off together (standing 0.16 s, moving 0.1 s, sprinting a bit faster).
	local prepStand = ctx.LoadClip("Tulevo_JumpPrep")
	local prepMove = ctx.LoadClip("Tulevo_JumpPrepMove")
	prepStand.Priority = Enum.AnimationPriority.Action
	prepMove.Priority = Enum.AnimationPriority.Action
	local prep = prepStand
	preparing = false
	humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping, false)
	jumpConnection = UserInputService.JumpRequest:Connect(function()
		if preparing or humanoid.Health <= 0 or Input.rollModifier() or Input.rollPending() then
			return -- Space while aiming is a roll, not a jump
		end
		local st = humanoid:GetState()
		local seat = humanoid.SeatPart
		if seat and seat:IsA("VehicleSeat") then
			return -- in a car Space is the handbrake; F gets out (Client.Vehicles)
		end
		if humanoid.Sit or st == Enum.HumanoidStateType.Seated or st == Enum.HumanoidStateType.Climbing
			or st == Enum.HumanoidStateType.Swimming
		then
			-- getting out of seats/cars, off ladders and out of water: plain Roblox jump
			preparing = true
			humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping, true)
			humanoid.Jump = true
			task.delay(0.3, function()
				humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping, false)
				preparing = false
			end)
			return
		end
		if not ctx.Grounded then
			return
		end
		preparing = true
		local m = Config.Movement
		ctx.JumpKind = if ctx.Speed < 1.5 and not ctx.Wants
			then "Stand"
			elseif ctx.Speed >= m.JogSpeed + 2 then "Sprint"
			else "Move"
		prep = if ctx.JumpKind == "Stand" then prepStand else prepMove
		local rate = if ctx.JumpKind == "Sprint" then 1.3 else 1
		prep:Play(0.04, 1, rate)
		local windUp = (if prep.Length > 0 then prep.Length else 0.12) / rate
		emit("Prep", ctx.JumpKind, windUp)
		task.delay(windUp, function()
			if humanoid.Health > 0 and humanoid.FloorMaterial ~= Enum.Material.Air then
				humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping, true)
				humanoid:ChangeState(Enum.HumanoidStateType.Jumping)
				emit("TakeOff", ctx.JumpKind)
			end
			prep:Stop(0.08)
			task.delay(0.3, function()
				humanoid:SetStateEnabled(Enum.HumanoidStateType.Jumping, false)
				preparing = false
			end)
		end)
	end)

	local gait = Gait.new(ctx)
	local walkSpeed = humanoid.WalkSpeed

	connection = RunService.RenderStepped:Connect(function(dt)
		if humanoid.Health <= 0 or not character.Parent then
			return
		end
		local v = root.AssemblyLinearVelocity
		ctx.Speed = Vector3.new(v.X, 0, v.Z).Magnitude
		ctx.Grounded = humanoid.FloorMaterial ~= Enum.Material.Air and GROUND_STATES[humanoid:GetState()] == true
		ctx.Wants = humanoid.MoveDirection.Magnitude > 0.05

		-- keep the current move while it may continue, unless a higher one wants in
		local pick = nil
		for _, move in moves do
			if move == current then
				local keep = if move.KeepGoing then move.KeepGoing(ctx) else move.CanStart(ctx)
				if keep then
					pick = move
					break
				end
			elseif move.CanStart(ctx) then
				pick = move
				break
			end
		end
		if pick then
			setMove(pick)
		end
		if not current then
			return
		end
		if current.Update then
			current.Update(ctx, dt)
		end

		-- ease WalkSpeed toward the move's speed (GTA-style build-up, quicker slow-down)
		local target = if current.Speed then current.Speed(ctx) else Config.Movement.WalkSpeed
		local accel = Config.Movement.Acceleration
		if walkSpeed < target then
			walkSpeed = math.min(target, walkSpeed + accel * dt)
		else
			walkSpeed = math.max(target, walkSpeed - accel * 2 * dt)
		end
		if math.abs(humanoid.WalkSpeed - walkSpeed) > 0.01 then
			humanoid.WalkSpeed = walkSpeed
		end

		gait:update(dt, current.UsesGait ~= false)
	end)

	humanoid.Died:Connect(function()
		gait:stop()
	end)
end

-- Where the player looks from and toward (Movement/FirstPersonCamera: real eye position in first
-- person, no roll tumble): use it for aiming.
Movement.view = FirstPersonCamera.view
Movement.viewFocus = FirstPersonCamera.focus

function Movement.start()
	local player = Players.LocalPlayer
	FirstPersonCamera.start(function()
		return current ~= nil and current.Name == "Roll"
	end)
	player.CharacterAdded:Connect(bind)
	if player.Character then
		task.spawn(bind, player.Character)
	end
end

return Movement
