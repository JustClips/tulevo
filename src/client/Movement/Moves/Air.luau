-- In the air: GTA-style take-off (Tulevo_Jump), then the falling loop (Tulevo_Fall), and a
-- landing dip (Tulevo_Land) when you touch down after a real jump or drop. Keeps the speed
-- you jumped with (a sprint jump stays fast). Short drops off a kerb skip the fall pose.
local FALL_DELAY = 0.2 -- seconds of falling (without jumping) before the fall pose shows
local LAND_AFTER = 0.3 -- seconds in the air before a landing dip plays

local function clips(ctx)
	if not ctx.Air then
		local c = {
			jump = ctx.LoadClip("Tulevo_Jump"),
			fall = ctx.LoadClip("Tulevo_Fall"),
			land = ctx.LoadClip("Tulevo_Land"),
		}
		for name, t in c do
			t.Priority = Enum.AnimationPriority.Movement
			t.Looped = name == "fall"
		end
		c.time, c.jumped, c.speed = 0, false, 16
		ctx.Air = c
	end
	return ctx.Air
end

return {
	Name = "Air",
	Priority = 20,
	UsesGait = false,
	CanStart = function(ctx)
		return not ctx.Grounded
	end,
	Speed = function(ctx)
		return clips(ctx).speed
	end,
	Start = function(ctx)
		local c = clips(ctx)
		c.time = 0
		c.speed = ctx.Humanoid.WalkSpeed
		c.land:Stop(0.05)
		c.jumped = ctx.Humanoid:GetState() == Enum.HumanoidStateType.Jumping
		if c.jumped then
			c.jump:Play(0.08, 1, 1)
		end
	end,
	Update = function(ctx, dt)
		local c = clips(ctx)
		c.time += dt
		if c.fall.IsPlaying then
			return
		end
		local jumpDone = c.jumped and (not c.jump.IsPlaying or c.jump.TimePosition >= c.jump.Length - 0.05)
		if jumpDone or (not c.jumped and c.time > FALL_DELAY) then
			c.fall:Play(if c.jumped then 0.3 else 0.2, 1, 1)
		end
	end,
	Stop = function(ctx)
		local c = clips(ctx)
		c.jump:Stop(0.1)
		c.fall:Stop(0.12)
		if c.time > LAND_AFTER and ctx.Humanoid.Health > 0 then
			-- running landings are a quick, lighter dip so you keep moving
			local moving = ctx.Wants and ctx.Speed > 2
			c.land:Play(0.05, if moving then 0.5 else 1, if moving then 1.5 else 1)
		end
	end,
}
