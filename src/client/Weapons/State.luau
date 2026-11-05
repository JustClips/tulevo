-- Small shared state so other client systems (Movement's Aim move, HUD) can read the
-- weapon state without requiring the weapon controller.
return {
	Equipped = nil :: string?, -- weapon id in hand
	Aiming = false,
	Reloading = false,
	Mag = 0,
	Reserve = 0,
}
