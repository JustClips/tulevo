--[[
	Movement: the on-foot move system for the local character.

	Every move is a module in Movement/Moves. Each frame the controller asks the moves which
	ones want to run and picks the one with the highest Priority. The active move sets the
	target WalkSpeed and can run its own code. Walking, jogging and sprinting share one foot
	animation layer (Movement/Gait) that blends the clips by real speed so feet stay planted.

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
	Speed (horizontal studs/s), Grounded, Wants (stick/WASD pushed), Active (move name),
	LoadClip(name) -> AnimationTrack (ids from Shared.AnimIds).
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local AnimIds = require(Shared:WaitForChild("AnimIds"))
local Input = require(script:WaitForChild("Input"))
local Gait = require(script:WaitForChild("Gait"))

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
local current = nil -- the active move
local ctx = nil

function Movement.active(): string?
	return current and current.Name
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

function Movement.start()
	local player = Players.LocalPlayer
	player.CharacterAdded:Connect(bind)
	if player.Character then
		task.spawn(bind, player.Character)
	end
end

return Movement
