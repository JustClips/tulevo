-- Combat roll: Ctrl + Space (gamepad B + A, phone Roll button). Rolls toward the way you're
-- pushing, relative to where the character faces: forward, back, left or right (standing
-- still = forward). Keeps facing the same way during the roll, then hands back control.
local CLIPS = {
	Forward = "Tulevo_RollForward",
	Back = "Tulevo_RollBack",
	Left = "Tulevo_RollLeft",
	Right = "Tulevo_RollRight",
}

local function state(ctx)
	if not ctx.Roll then
		local tracks = {}
		for dir, name in CLIPS do
			local t = ctx.LoadClip(name)
			t.Priority = Enum.AnimationPriority.Movement
			t.Looped = false
			tracks[dir] = t
		end
		ctx.Roll = { tracks = tracks, track = nil, dir = Vector3.zero, t = 0, length = 0.95, readyAt = 0 }
	end
	return ctx.Roll
end

local function pick(ctx): (string, Vector3)
	local root = ctx.Root
	local move = ctx.Humanoid.MoveDirection
	if move.Magnitude < 0.1 then
		local look = root.CFrame.LookVector
		return "Forward", Vector3.new(look.X, 0, look.Z).Unit
	end
	local localDir = root.CFrame:VectorToObjectSpace(move)
	local dir = Vector3.new(move.X, 0, move.Z).Unit
	if math.abs(localDir.Z) >= math.abs(localDir.X) then
		return if localDir.Z < 0 then "Forward" else "Back", dir
	end
	return if localDir.X > 0 then "Right" else "Left", dir
end

return {
	Name = "Roll",
	Priority = 30,
	UsesGait = false,
	CanStart = function(ctx)
		return ctx.Input.rollPending() and ctx.Grounded and os.clock() >= state(ctx).readyAt
	end,
	KeepGoing = function(ctx)
		local s = state(ctx)
		return s.t < s.length and ctx.Humanoid.Health > 0
	end,
	Speed = function(ctx)
		return ctx.Config.Movement.RollSpeed
	end,
	Start = function(ctx)
		local s = state(ctx)
		ctx.Input.takeRoll()
		local name, dir = pick(ctx)
		s.dir, s.t = dir, 0
		s.track = s.tracks[name]
		s.track:Play(0.06, 1, 1)
		s.length = if s.track.Length > 0 then s.track.Length else 0.95
		ctx.Humanoid.AutoRotate = false
	end,
	Update = function(ctx, dt)
		local s = state(ctx)
		s.t += dt
		-- slower while crouching into it, full speed through the roll, easing off as you stand
		local u = s.t / s.length
		local f = if u < 0.13 then 0.6 + 0.4 * u / 0.13 elseif u < 0.68 then 1 else 1 - 0.7 * (u - 0.68) / 0.32
		local speed = ctx.Config.Movement.RollSpeed * f
		local v = ctx.Root.AssemblyLinearVelocity
		ctx.Root.AssemblyLinearVelocity = Vector3.new(s.dir.X * speed, v.Y, s.dir.Z * speed)
	end,
	Stop = function(ctx)
		local s = state(ctx)
		if s.track then
			s.track:Stop(0.12)
		end
		ctx.Humanoid.AutoRotate = true
		s.readyAt = os.clock() + ctx.Config.Movement.RollCooldown
	end,
}
