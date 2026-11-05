--[[
	GTA-style walk and run for the local R15 character.

	Plays Tulevo_Walk / Tulevo_Run (art/anim/locomotion.py) at Movement priority, above the
	default Animate script, and scales their speed to how fast the character really moves so
	the feet stay planted. Walk is the default; hold Shift or click the left stick to run.
	Animations on your own character replicate, so everyone sees them.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local AnimIds = require(Shared:WaitForChild("AnimIds"))

local player = Players.LocalPlayer

-- Studs per second each clip covers at playback speed 1 (printed by locomotion.py).
local WALK_NATURAL = 2.97
local RUN_NATURAL = 6.56
local MAX_RATE = 2.0 -- above this the legs look frantic; a little foot slide reads better
local DEFAULT_GROUND = 3.19 -- default R15: HipHeight 2.19 + half the root part

local runHeld = false
local runToggled = false
local analogInput = false

local function isRunning()
	return runHeld or runToggled
end

UserInputService.InputBegan:Connect(function(input, processed)
	if input.KeyCode == Enum.KeyCode.LeftShift or input.KeyCode == Enum.KeyCode.RightShift then
		runHeld = true
	elseif input.KeyCode == Enum.KeyCode.ButtonL3 and not processed then
		runToggled = not runToggled
	end
end)

UserInputService.InputEnded:Connect(function(input)
	if input.KeyCode == Enum.KeyCode.LeftShift or input.KeyCode == Enum.KeyCode.RightShift then
		runHeld = false
	end
end)

local function updateInputKind()
	local t = UserInputService:GetLastInputType()
	analogInput = t == Enum.UserInputType.Touch or t.Name:sub(1, 7) == "Gamepad"
	if not analogInput then
		runToggled = false
	end
end
UserInputService.LastInputTypeChanged:Connect(updateInputKind)
updateInputKind()

local function loadTrack(animator: Animator, id: string): AnimationTrack
	local anim = Instance.new("Animation")
	anim.AnimationId = id
	local track = animator:LoadAnimation(anim)
	track.Priority = Enum.AnimationPriority.Movement
	track.Looped = true
	return track
end

local connection: RBXScriptConnection? = nil

local function onCharacter(character: Model)
	if connection then
		connection:Disconnect()
		connection = nil
	end
	local humanoid = character:WaitForChild("Humanoid") :: Humanoid
	local root = character:WaitForChild("HumanoidRootPart") :: BasePart
	if humanoid.RigType ~= Enum.HumanoidRigType.R15 then
		return
	end
	local animator = humanoid:WaitForChild("Animator") :: Animator

	local walk = loadTrack(animator, AnimIds.Tulevo_Walk)
	local run = loadTrack(animator, AnimIds.Tulevo_Run)
	walk:Play(0, 0.001, 1)
	run:Play(0, 0.001, 1)

	local weight = 0 -- how much of the walk/run layer shows (0 standing / in the air)
	local blend = 0 -- 0 = walk, 1 = run
	local lastW, lastR = -1, -1

	connection = RunService.RenderStepped:Connect(function(dt)
		if humanoid.Health <= 0 or not walk.IsPlaying then
			return
		end

		-- GTA controls: walk unless running; analog sticks choose their own pace.
		local target = if analogInput or isRunning() then Config.RunSpeed else Config.WalkSpeed
		if humanoid.WalkSpeed ~= target then
			humanoid.WalkSpeed = target
		end

		local v = root.AssemblyLinearVelocity
		local speed = Vector3.new(v.X, 0, v.Z).Magnitude
		local state = humanoid:GetState()
		local grounded = humanoid.FloorMaterial ~= Enum.Material.Air
			and (state == Enum.HumanoidStateType.Running or state == Enum.HumanoidStateType.RunningNoPhysics)
		local moving = grounded and speed > 0.6 and humanoid.MoveDirection.Magnitude > 0.05

		local k = math.min(1, dt * 12)
		weight += ((if moving then 1 else 0) - weight) * k
		local runFrom, runTo = Config.WalkSpeed + 1, Config.RunSpeed * 0.8
		local wantBlend = math.clamp((speed - runFrom) / math.max(0.1, runTo - runFrom), 0, 1)
		local before = blend
		blend += (wantBlend - blend) * math.min(1, dt * 8)

		-- When the run starts showing, line its step up with the walk's current step.
		if before < 0.02 and blend >= 0.02 and walk.Length > 0 and run.Length > 0 then
			run.TimePosition = (walk.TimePosition / walk.Length) * run.Length
		elseif before > 0.98 and blend <= 0.98 and walk.Length > 0 and run.Length > 0 then
			walk.TimePosition = (run.TimePosition / run.Length) * walk.Length
		end

		-- Bigger avatars take longer steps.
		local size = (humanoid.HipHeight + root.Size.Y / 2) / DEFAULT_GROUND
		local rateSpeed = math.max(speed, 1)
		walk:AdjustSpeed(math.clamp(rateSpeed / (WALK_NATURAL * size), 0.5, MAX_RATE))
		run:AdjustSpeed(math.clamp(rateSpeed / (RUN_NATURAL * size), 0.5, MAX_RATE))

		local ww = math.max(0.001, weight * (1 - blend))
		local wr = math.max(0.001, weight * blend)
		if math.abs(ww - lastW) > 0.01 then
			walk:AdjustWeight(ww, 0)
			lastW = ww
		end
		if math.abs(wr - lastR) > 0.01 then
			run:AdjustWeight(wr, 0)
			lastR = wr
		end
	end)

	humanoid.Died:Connect(function()
		walk:Stop(0.2)
		run:Stop(0.2)
	end)
end

player.CharacterAdded:Connect(onCharacter)
if player.Character then
	task.spawn(onCharacter, player.Character)
end
