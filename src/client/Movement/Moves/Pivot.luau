-- Quick turn: reverse the stick while running and you plant, dip and drive off the other way
-- (Tulevo_Pivot, art/anim/steps.py), turning round in one go instead of the body spinning on
-- the spot. Not while the gun is up (the body faces the aim then).
local LENGTH = 0.4 -- clip length
local BRAKE = 0.14 -- seconds to kill the old speed
local TURN_START, TURN_TIME = 0.04, 0.24

local function state(ctx)
	if not ctx.Pivot then
		local track = ctx.LoadClip("Tulevo_Pivot")
		track.Priority = Enum.AnimationPriority.Movement
		track.Looped = false
		ctx.Pivot = { track = track, t = 0, from = Vector3.zero, to = Vector3.zero, speed = 0, fromYaw = 0, turn = 0 }
	end
	return ctx.Pivot
end

local function flat(v: Vector3): Vector3
	return Vector3.new(v.X, 0, v.Z)
end

local function yawOf(dir: Vector3): number
	return math.atan2(-dir.X, -dir.Z)
end

local function smooth(u: number): number
	u = math.clamp(u, 0, 1)
	return u * u * (3 - 2 * u)
end

local function targetSpeed(ctx): number
	local m = ctx.Config.Movement
	return if ctx.Input.isDown("Sprint") then m.SprintSpeed else m.JogSpeed
end

return {
	Name = "Pivot",
	Priority = 11,
	UsesGait = false,
	CanStart = function(ctx)
		if not (ctx.Grounded and ctx.Wants and ctx.Humanoid.AutoRotate) then
			return false
		end
		if ctx.Active ~= "Sprint" and ctx.Active ~= "Walk" then
			return false
		end
		if ctx.Speed < ctx.Config.Movement.JogSpeed * 0.7 then
			return false
		end
		local v = flat(ctx.Root.AssemblyLinearVelocity)
		local move = flat(ctx.Humanoid.MoveDirection)
		return v.Magnitude > 0.1 and move.Magnitude > 0.1 and v.Unit:Dot(move.Unit) < -0.6
	end,
	KeepGoing = function(ctx)
		return state(ctx).t < LENGTH and ctx.Grounded and ctx.Humanoid.Health > 0
	end,
	Speed = targetSpeed,
	Start = function(ctx)
		local s = state(ctx)
		local v = flat(ctx.Root.AssemblyLinearVelocity)
		s.t, s.speed = 0, v.Magnitude
		s.from = v.Unit
		s.to = flat(ctx.Humanoid.MoveDirection).Unit
		local look = flat(ctx.Root.CFrame.LookVector)
		s.fromYaw = if look.Magnitude > 0.01 then yawOf(look.Unit) else yawOf(s.from)
		s.turn = (yawOf(s.to) - s.fromYaw + math.pi) % (2 * math.pi) - math.pi
		ctx.Humanoid.AutoRotate = false
		s.track:Play(0.06, 1, 1)
	end,
	Update = function(ctx, dt)
		local s = state(ctx)
		s.t += dt
		-- turn the body round over the plant
		local yaw = s.fromYaw + s.turn * smooth((s.t - TURN_START) / TURN_TIME)
		ctx.Root.CFrame = CFrame.new(ctx.Root.Position) * CFrame.Angles(0, yaw, 0)
		ctx.Root.AssemblyAngularVelocity = Vector3.zero
		-- brake the old way, then drive off the new way
		local vel
		if s.t < BRAKE then
			vel = s.from * s.speed * (1 - s.t / BRAKE)
		else
			vel = s.to * targetSpeed(ctx) * 0.8 * smooth((s.t - BRAKE) / (LENGTH - BRAKE))
		end
		local v = ctx.Root.AssemblyLinearVelocity
		ctx.Root.AssemblyLinearVelocity = Vector3.new(vel.X, v.Y, vel.Z)
	end,
	Stop = function(ctx)
		state(ctx).track:Stop(0.15)
		ctx.Humanoid.AutoRotate = true
	end,
}
