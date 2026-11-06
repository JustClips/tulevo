--[[
	Carbine Rifle (AR-15 style carbine, model Shared.ModelIds.CarbineRifle).
	Every number that decides how it plays is here. Damage is per bullet before the body-part
	multiplier and distance falloff:
		final damage = Damage * BodyDamage[part hit] * falloff
	falloff = 1 up to FalloffStart studs, then drops in a straight line to FalloffMin at Range.
	Past Range a bullet does nothing.
]]
return {
	Id = "CarbineRifle",
	Name = "Carbine Rifle",
	ClassName = "Rifle", -- held with the Rifle animations (art/anim/gun.py)
	Weight = 3.4, -- kg in the inventory
	Cells = Vector2.new(4, 2), -- inventory cells, wide x tall (R turns it while dragging)
	Model = "CarbineRifle", -- Shared.ModelIds
	Description = "AR-15 style carbine. Reloads from Rifle ammo in your bag.",
	Ammo = "RifleAmmo", -- inventory item it reloads from (Shared/Items/Defs.luau)

	-- damage
	Damage = 24, -- one bullet to the chest at close range
	BodyDamage = { -- multiplier per body part hit (anything missing uses Config.Weapons.BodyDamage)
		Head = 2.5,
		UpperTorso = 1.0,
		LowerTorso = 0.9,
		LeftUpperArm = 0.7,
		RightUpperArm = 0.7,
		LeftLowerArm = 0.6,
		RightLowerArm = 0.6,
		LeftHand = 0.5,
		RightHand = 0.5,
		LeftUpperLeg = 0.75,
		RightUpperLeg = 0.75,
		LeftLowerLeg = 0.6,
		RightLowerLeg = 0.6,
		LeftFoot = 0.5,
		RightFoot = 0.5,
	},
	Range = 450, -- studs
	FalloffStart = 120, -- studs of full damage
	FalloffMin = 0.5, -- damage share left at Range

	-- firing
	FireRate = 10, -- shots per second (600 rounds per minute)
	Automatic = true, -- hold to keep firing; false = one shot per click
	Spread = 2.5, -- degrees, firing from the hip
	AimSpread = 0.6, -- degrees, aiming

	-- magazine
	MagSize = 30, -- bullets in a full magazine
	ReserveAmmo = 150, -- Rifle ammo you spawn with in the bag (5 more mags)
	ReloadTime = 2.45, -- seconds; = Weapon_Rifle_Reload / ReloadPouch length so the mag swap lines up
	AutoReload = true, -- pulling the trigger on an empty mag reloads
}
