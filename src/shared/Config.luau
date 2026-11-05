-- Shared settings, readable from server and client:
-- require(game.ReplicatedStorage.Shared.Config)
local Config = {
	GameName = "Tulevo",

	-- On foot (GTA style), used by StarterPlayerScripts.Client.Movement.
	-- Keyboard: walk, hold Shift to sprint. Gamepad: stick pushed a little = walk, all the
	-- way = jog, click the left stick to sprint. Phones: same stick, plus a Sprint button.
	-- Crouch (toggle): Ctrl or C, gamepad B, phone Crouch button.
	-- Roll: Ctrl + Space (gamepad B + A, phone Roll button), toward the way you're moving.
	Movement = {
		WalkSpeed = 6,
		JogSpeed = 14,
		SprintSpeed = 20,
		CrouchSpeed = 4,
		CrouchCameraDrop = 1.3, -- camera sits this much lower while crouched
		RollSpeed = 17, -- studs/s during a roll (Ctrl + Space)
		RollCooldown = 0.5, -- seconds after a roll before the next one
		Acceleration = 40, -- studs/s per second when speeding up (slowing down is 2x)
	},

	Weapons = {
		-- everyone gets these on join (no shop/pickups yet), and spawns holding EquipOnSpawn
		DefaultLoadout = { "Rifle" },
		EquipOnSpawn = "Rifle",
		-- extra weapons in Studio play tests only (they have no models or animations yet)
		StudioLoadout = { "Bat", "Pistol", "SMG", "Shotgun" },
		-- the carbine is exported at 3.6 studs per meter; our ~5 stud characters are ~2.9, so
		-- guns are shown at this scale. The rifle animations (art/anim/gun.py GUN_SCALE) are
		-- solved for it, so change both together.
		GunScale = 0.85,
		AimFieldOfView = 55, -- camera zooms in a little while aiming (normal is 70)
		LowerNearWalls = 2.4, -- studs: closer than this to a wall, the gun points down
		-- number keys pick a wheel slot (GTA-style wheel UI comes later)
		SlotKeys = { "Melee", "Pistol", "SMG", "Shotgun", "Rifle" },
	},

	-- Cars (docs/vehicles.md). Get in with F (gamepad Y, tap the prompt on phones), out with F again.
	-- W/S or triggers = gas/brake/reverse, A/D or stick = steer, Space / RB = handbrake.
	Vehicles = {
		EnterDistance = 8, -- studs from the driver's door
		-- parked next to the spawn on start; Offset from the spawn, Yaw 0 = facing north (-Z)
		TestCars = {
			{ Id = "Sedan", Offset = Vector3.new(9, 0, -14), Yaw = 0 },
			{ Id = "Hypercar", Offset = Vector3.new(-9, 0, -14), Yaw = 0 },
		},
	},

	-- Every avatar spawns as R15 (CharacterSetup.server.luau). Sizes are clamped to this
	-- range so tiny, giant or stretched avatars still look human next to cars and doors.
	Character = {
		HeightMin = 0.9,
		HeightMax = 1.05,
		WidthMin = 0.8,
		WidthMax = 1.0,
		HeadMin = 0.95,
		HeadMax = 1.0,
		BodyTypeMax = 0.3, -- 0 = classic blocky proportions, 1 = full Rthro
		ProportionMax = 0.0,
	},
}

return Config
