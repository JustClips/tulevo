-- Starting to move from standing: instead of popping straight into the walk/run loop you lean
-- in and take a first step (Tulevo_StartWalk, or Tulevo_StartRun when you set off jogging or
-- sprinting: dip, push off the back foot, drive the knee). The loop fades in under it
-- (Config.Movement.BlendTime). Off with Config.Movement.StartStopSteps = false.
local STILL = 0.15 -- seconds standing still before a start step plays

local function state(ctx)
	if not ctx.StartStep then
		local walk = ctx.LoadClip("Tulevo_StartWalk")
		local run = ctx.LoadClip("Tulevo_StartRun")
		for _, t in { walk, run } do
			t.Priority = Enum.AnimationPriority.Movement
			t.Looped = false
		end
		ctx.StartStep = { walk = walk, run = run, track = walk, t = 0, length = 0.3, speed = 8 }
	end
	return ctx.StartStep
end

local function targetSpeed(ctx): number
	local m = ctx.Config.Movement
	if ctx.Input.isDown("Sprint") then
		return m.SprintSpeed
	end
	return if ctx.Input.analog() then m.JogSpeed else m.WalkSpeed
end

return {
	Name = "StartStep",
	Priority = 9, -- under Sprint's skid/pivot and everything else; above Walk
	UsesGait = false,
	CanStart = function(ctx)
		local m = ctx.Config.Movement
		return m.StartStopSteps ~= false
			and ctx.Wants
			and ctx.Grounded
			and ctx.StillBefore > STILL
			and (ctx.Active == "Walk" or ctx.Active == "StopStep" or ctx.Active == nil)
			and ctx.Humanoid.AutoRotate -- not while aiming (the body faces the aim then)
	end,
	KeepGoing = function(ctx)
		local s = state(ctx)
		return ctx.Wants and ctx.Grounded and s.t < s.length - ctx.Config.Movement.BlendTime * 0.5
	end,
	Speed = function(ctx)
		return state(ctx).speed
	end,
	Start = function(ctx)
		local s = state(ctx)
		s.speed = targetSpeed(ctx)
		local running = s.speed > ctx.Config.Movement.WalkSpeed + 1
		s.track = if running then s.run else s.walk
		s.t = 0
		s.track:Play(0.1, 1, 1)
		s.length = if s.track.Length > 0 then s.track.Length else 0.32
	end,
	Update = function(ctx, dt)
		state(ctx).t += dt
	end,
	Stop = function(ctx)
		state(ctx).track:Stop(ctx.Config.Movement.BlendTime)
	end,
}
