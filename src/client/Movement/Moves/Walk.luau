-- Default on-foot move. Keyboard walks at WalkSpeed; analog sticks get up to JogSpeed so a
-- light push walks and a full push jogs.
return {
	Name = "Walk",
	Priority = 0,
	CanStart = function()
		return true
	end,
	Speed = function(ctx)
		local m = ctx.Config.Movement
		return if ctx.Input.analog() then m.JogSpeed else m.WalkSpeed
	end,
}
