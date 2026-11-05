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
	Twist = 0, -- radians the chest turns from the hips (0: the whole body faces the aim)
	Pitch = 0, -- radians the waist bends to aim up (+) / down (-)
	GaitReverse = false, -- aiming while walking backwards: the walk/run clips play in reverse
	StrafeSide = 0, -- aiming: sideways share of the movement (+ right, - left) for the side-step clips
	AimBlend = 0, -- 0..1 how much the Aim pose is in: Weapons/GunPose locks the chest to the aim by this much
	HipTurn = 0, -- radians the hips are turned right of the aim (rifle stance, set by Weapons/GunPose)
}
