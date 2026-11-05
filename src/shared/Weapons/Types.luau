-- Type shapes for weapon data. See Weapons/init.luau.

-- GTA-style wheel slots: one weapon per slot is carried at a time.
export type Slot = "Melee" | "Pistol" | "SMG" | "Shotgun" | "Rifle" | "Sniper" | "Heavy" | "Throwable"

export type ClassDef = {
	Name: string,
	Slot: Slot,
	Kind: "Gun" | "Melee" | "Throwable",
	-- animation slot names this class needs; ids come from Shared.AnimIds as
	-- "Weapon_<Class>_<Slot>" (for example Weapon_Pistol_Fire). Missing ids just don't play.
	Anims: { string },
	AimWalkSpeed: number, -- WalkSpeed while aiming
	CanSprintWhileHeld: boolean,
	TwoHanded: boolean,
}

export type WeaponDef = {
	Id: string,
	Name: string,
	ClassName: string,
	Class: ClassDef?, -- filled in by the registry
	Weight: number, -- kg in the inventory (Shared/Items, Config.Inventory carry limits)

	-- guns
	Damage: number?, -- per pellet/bullet at close range
	HeadshotMultiplier: number?,
	FireRate: number?, -- shots per second
	Automatic: boolean?,
	Pellets: number?, -- shotguns > 1
	Spread: number?, -- degrees, hip fire
	AimSpread: number?, -- degrees, aimed
	Range: number?, -- studs, no damage past this
	FalloffStart: number?, -- studs, damage drops linearly to FalloffMin at Range
	FalloffMin: number?, -- damage share left at Range (default 0.5)
	BodyDamage: { [string]: number }?, -- multiplier per body part hit (falls back to Config.Weapons.BodyDamage; HeadshotMultiplier still works for Head)
	MaxReserve: number?, -- most spare bullets you can carry
	AutoReload: boolean?, -- trigger on an empty mag reloads (default true)
	MagSize: number?,
	ReserveAmmo: number?, -- spare rounds you spawn with
	ReloadTime: number?,

	-- melee
	SwingTime: number?,
	Reach: number?,

	-- art (filled in once models exist)
	Model: string?, -- asset name / id, welded to the right hand at the "Grip" attachment
	Sounds: { [string]: string }?, -- Fire, Reload, Equip, Empty
}

return {}
