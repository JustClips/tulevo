-- Small shared state so other client systems (Movement's Aim move, Gait, HUD) can read the
-- weapon state without requiring the weapon controller.
return {
	Equipped = nil :: string?, -- weapon id in hand
	Aiming = false, -- aim button held (or phone toggle)
	Raised = false, -- gun up at the shoulder: aiming, or just fired from the hip
	Reloading = false,
	Mag = 0,
	Reserve = 0,
	InVehicle = false, -- set by Client.Vehicles; no weapons while driving
	-- set by the controller for Weapons/GunPose and Movement/Gait
	Twist = 0, -- radians the chest turns back toward the camera while the hips follow the stick
	Pitch = 0, -- radians the waist bends to aim up (+) / down (-)
	GaitReverse = false, -- aiming while walking backwards: the walk/run clips play in reverse
}
