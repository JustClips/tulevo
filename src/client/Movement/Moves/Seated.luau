-- Sitting (car driver's seat, benches): beats every other move so nothing else runs, and
-- the walk/run layer fades out so the sit pose shows. Cars are driven by Client.Vehicles.
return {
	Name = "Seated",
	Priority = 100,
	UsesGait = false,
	CanStart = function(ctx)
		return ctx.Humanoid.SeatPart ~= nil
	end,
	Stop = function(ctx)
		-- don't come out of a car crouched or sprinting from keys pressed while driving
		ctx.Input.release("Sprint")
		ctx.Input.release("Crouch")
	end,
}
