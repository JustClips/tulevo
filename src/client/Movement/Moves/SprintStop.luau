-- Sprint skid-stop: let go of the stick mid-sprint and you plant the front heel, sit down, lean
-- back and skid a short way instead of halting dead (Tulevo_SprintStop, art/anim/steps.py).
-- Pushing the stick again after the plant carries straight on.
local LENGTH = 0.62 -- clip length
local SKID = 0.38 -- seconds the body keeps sliding

local function state(ctx)
	if not ctx.SprintStop then
		local track = ctx.LoadClip("Tulevo_SprintStop")
		track.Priority = Enum.AnimationPriority.Movement
		track.Looped = false
		ctx.SprintStop = { track = track, t = 0, dir = Vector3.zero, speed = 0 }
	end
	return ctx.SprintStop
end

return {
	Name = "SprintStop",
	Priority = 11,
	UsesGait = false,
	CanStart = function(ctx)
		return ctx.Active == "Sprint" and not ctx.Wants and ctx.Grounded and ctx.Speed > ctx.Config.Movement.JogSpeed
	end,
	KeepGoing = function(ctx)
		local s = state(ctx)
		return s.t < LENGTH and ctx.Grounded and not (ctx.Wants and s.t > 0.2) and ctx.Humanoid.Health > 0
	end,
	Speed = function(ctx)
		return ctx.Config.Movement.WalkSpeed
	end,
	Start = function(ctx)
		local s = state(ctx)
		local v = ctx.Root.AssemblyLinearVelocity
		local flat = Vector3.new(v.X, 0, v.Z)
		s.t, s.speed = 0, flat.Magnitude
		s.dir = if flat.Magnitude > 0.1 then flat.Unit else Vector3.zero
		s.track:Play(0.08, 1, 1)
	end,
	Update = function(ctx, dt)
		local s = state(ctx)
		s.t += dt
		if s.t < SKID then
			-- slide to a stop (quick at first, then easing off)
			local speed = s.speed * (1 - s.t / SKID) ^ 1.6
			local v = ctx.Root.AssemblyLinearVelocity
			ctx.Root.AssemblyLinearVelocity = Vector3.new(s.dir.X * speed, v.Y, s.dir.Z * speed)
		end
	end,
	Stop = function(ctx)
		state(ctx).track:Stop(0.15)
	end,
}
