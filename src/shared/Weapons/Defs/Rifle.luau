return {
	Id = "Rifle",
	Name = "Assault Rifle",
	ClassName = "Rifle",
	Damage = 20,
	HeadshotMultiplier = 1.8,
	FireRate = 9,
	Automatic = true,
	Spread = 3,
	AimSpread = 0.8,
	Range = 400,
	FalloffStart = 100,
	MagSize = 30,
	ReserveAmmo = 180,
	ReloadTime = 2.3, -- = Weapon_Rifle_Reload length, so the mag swap lines up
	Model = "CarbineRifle", -- Shared.ModelIds; held with the Rifle class animations (art/anim/gun.py)
}
