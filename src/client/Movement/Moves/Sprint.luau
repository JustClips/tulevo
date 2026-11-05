-- Sprint: hold Shift (or toggle with left-stick click / the phone button) while moving.
-- Keeps going in the air so a jump doesn't cut your speed.
return {
	Name = "Sprint",
	Priority = 10,
	CanStart = function(ctx)
		return ctx.Input.isDown("Sprint") and ctx.Wants and ctx.Grounded
	end,
	KeepGoing = function(ctx)
		return ctx.Input.isDown("Sprint") and ctx.Wants
	end,
	Speed = function(ctx)
		return ctx.Config.Movement.SprintSpeed
	end,
	Start = function(ctx)
		ctx.Input.release("Crouch") -- sprinting stands you up, like GTA
	end,
	Stop = function(ctx)
		-- a toggled sprint ends when you stop moving, like GTA
		if not ctx.Wants then
			ctx.Input.release("Sprint")
		end
	end,
}
