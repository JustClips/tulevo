-- Letting go of the stick while walking or jogging: instead of freezing in place you take one
-- or two shortening steps (Tulevo_StopWalk), or two-three braking steps from a run
-- (Tulevo_StopRun), and settle. The body slows down with the steps. Sprinting has its own
-- skid stop (Moves/SprintStop). Pushing the stick again carries straight on.
-- Off with Config.Movement.StartStopSteps = false.
local function state(ctx)
	if not ctx.StopStep then
		local walk = ctx.LoadClip("Tulevo_StopWalk")
		local run = ctx.LoadClip("Tulevo_StopRun")
		for _, t in { walk, run } do
			t.Priority = Enum.AnimationPriority.Movement
			t.Looped = false
		end
		ctx.StopStep = { walk = walk, run = run, track = walk, t = 0, length = 0.5, dir = Vector3.zero, speed = 0, slide = 0.3 }
	end
	return ctx.StopStep
end

return {
	Name = "StopStep",
	Priority = 9,
	UsesGait = false,
	CanStart = function(ctx)
		local m = ctx.Config.Movement
		return m.StartStopSteps ~= false
			and ctx.Active == "Walk"
			and not ctx.Wants
			and ctx.Grounded
			and ctx.Speed > 2.5
			and ctx.Humanoid.AutoRotate
	end,
	KeepGoing = function(ctx)
		local s = state(ctx)
		return s.t < s.length - ctx.Config.Movement.BlendTime * 0.5
			and ctx.Grounded
			and not (ctx.Wants and s.t > 0.1)
			and ctx.Humanoid.Health > 0
	end,
	Speed = function(ctx)
		return ctx.Config.Movement.WalkSpeed
	end,
	Start = function(ctx)
		local s = state(ctx)
		local m = ctx.Config.Movement
		local v = ctx.Root.AssemblyLinearVelocity
		local flat = Vector3.new(v.X, 0, v.Z)
		s.speed = flat.Magnitude
		s.dir = if flat.Magnitude > 0.1 then flat.Unit else Vector3.zero
		local running = s.speed > (m.WalkSpeed + m.JogSpeed) / 2
		s.track = if running then s.run else s.walk
		s.slide = if running then 0.5 else 0.3 -- seconds the steps carry you
		s.t = 0
		s.track:Play(0.12, 1, 1)
		s.length = if s.track.Length > 0 then s.track.Length else 0.5
	end,
	Update = function(ctx, dt)
		local s = state(ctx)
		s.t += dt
		local u = math.clamp(s.t / s.slide, 0, 1)
		local speed = s.speed * (1 - u) ^ 1.4 -- slows with each step
		local v = ctx.Root.AssemblyLinearVelocity
		ctx.Root.AssemblyLinearVelocity = Vector3.new(s.dir.X * speed, v.Y, s.dir.Z * speed)
	end,
	Stop = function(ctx)
		state(ctx).track:Stop(ctx.Config.Movement.BlendTime)
	end,
}
