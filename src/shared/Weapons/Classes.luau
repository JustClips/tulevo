-- Weapon classes: how a family of weapons is held, where it sits on the wheel and which
-- animations it needs (docs/weapons.md has the full list for whoever makes them).
local GUN_ANIMS = { "Hold", "Aim", "Fire", "Reload", "Equip" }

return {
	Melee = {
		Name = "Melee",
		Slot = "Melee",
		Kind = "Melee",
		Anims = { "Hold", "Attack1", "Attack2", "Attack3", "Equip" },
		AimWalkSpeed = 10,
		CanSprintWhileHeld = true,
		TwoHanded = false,
	},
	Pistol = {
		Name = "Pistol",
		Slot = "Pistol",
		Kind = "Gun",
		Anims = GUN_ANIMS,
		AimWalkSpeed = 8,
		CanSprintWhileHeld = true,
		TwoHanded = false,
	},
	SMG = {
		Name = "SMG",
		Slot = "SMG",
		Kind = "Gun",
		Anims = GUN_ANIMS,
		AimWalkSpeed = 7,
		CanSprintWhileHeld = true,
		TwoHanded = true,
	},
	Shotgun = {
		Name = "Shotgun",
		Slot = "Shotgun",
		Kind = "Gun",
		Anims = GUN_ANIMS,
		AimWalkSpeed = 6,
		CanSprintWhileHeld = true,
		TwoHanded = true,
	},
	Rifle = {
		Name = "Rifle",
		Slot = "Rifle",
		Kind = "Gun",
		-- extra poses: Sprint (carry across the chest), Tuck (rolls), Air (jumps/falls),
		-- Lowered (muzzle down near walls)
		-- JumpPrep / JumpUp / Land: the arms follow the both-feet jump (with a little bounce)
		-- Holster / Draw: over the right shoulder onto the back and off it again (Q / slot key)
		-- CrouchHold: high ready while crouched
		Anims = {
			"Hold", "Aim", "Fire", "Reload", "Equip", "Sprint", "Tuck", "Air", "Lowered",
			"JumpPrep", "JumpUp", "Land", "Holster", "Draw", "CrouchHold",
		},
		AimWalkSpeed = 6,
		CanSprintWhileHeld = true,
		TwoHanded = true,
	},
}
