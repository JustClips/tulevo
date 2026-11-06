-- Crouch (stealth walk): toggle with Ctrl / C, gamepad B or the phone button. Plays its own
-- crouch idle + crouch walk clips instead of the walk/run layer, and lowers the camera.
-- Jumping or sprinting stands you back up.
local TweenService = game:GetService("TweenService")

local IDLE_RATE = 1
local NATURAL = 2.46 -- Tulevo_CrouchWalk studs/s at speed 1 (art/anim/locomotion.py)
local MAX_RATE = 1.61 -- calm top cadence (locomotion.py CROUCH_CADENCE); faster speeds slide a little
local AIR = {
	[Enum.HumanoidStateType.Jumping] = true,
	[Enum.HumanoidStateType.Freefall] = true,
}

local function tracks(ctx)
	if not ctx.Crouch then
		local idle = ctx.LoadClip("Tulevo_CrouchIdle")
		local walk = ctx.LoadClip("Tulevo_CrouchWalk")
		for _, t in { idle, walk } do
			t.Priority = Enum.AnimationPriority.Movement
			t.Looped = true
		end
		ctx.Crouch = { idle = idle, walk = walk, mix = 0 }
	end
	return ctx.Crouch
end

local function camera(ctx, drop)
	TweenService:Create(ctx.Humanoid, TweenInfo.new(0.25, Enum.EasingStyle.Quad), {
		CameraOffset = Vector3.new(ctx.Humanoid.CameraOffset.X, -drop, 0), -- X = gun shoulder camera
	}):Play()
end

return {
	Name = "Crouch",
	Priority = 5,
	UsesGait = false,
	CanStart = function(ctx)
		return ctx.Input.isDown("Crouch") and ctx.Grounded
	end,
	KeepGoing = function(ctx)
		return ctx.Input.isDown("Crouch") and not AIR[ctx.Humanoid:GetState()]
	end,
	Speed = function(ctx)
		return ctx.Config.Movement.CrouchSpeed
	end,
	Start = function(ctx)
		local c = tracks(ctx)
		c.mix = if ctx.Speed > 0.6 then 1 else 0
		c.idle:Play(0.2, math.max(0.001, 1 - c.mix), IDLE_RATE)
		c.walk:Play(0.2, math.max(0.001, c.mix), 1)
		camera(ctx, ctx.Config.Movement.CrouchCameraDrop)
	end,
	Update = function(ctx, dt)
		local c = tracks(ctx)
		local moving = ctx.Wants and ctx.Speed > 0.6
		c.mix += ((if moving then 1 else 0) - c.mix) * math.min(1, dt * 10)
		c.idle:AdjustWeight(math.max(0.001, 1 - c.mix), 0)
		c.walk:AdjustWeight(math.max(0.001, c.mix), 0)
		local follow = ctx.Config.Movement.AnimRateFollowsSpeed == true
		c.walk:AdjustSpeed(if follow then math.clamp(math.max(ctx.Speed, 1) / NATURAL, 0.5, MAX_RATE) else 1)
	end,
	Stop = function(ctx)
		local c = tracks(ctx)
		c.idle:Stop(0.25)
		c.walk:Stop(0.25)
		camera(ctx, 0)
		ctx.Input.release("Crouch")
	end,
}
