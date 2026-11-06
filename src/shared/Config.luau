-- Shared settings, readable from server and client:
-- require(game.ReplicatedStorage.Shared.Config)
local Config = {
	GameName = "Tulevo",

	-- On foot (GTA style), used by StarterPlayerScripts.Client.Movement.
	-- Keyboard: walk, hold Shift to sprint. Gamepad: stick pushed a little = walk, all the
	-- way = jog, click the left stick to sprint. Phones: same stick, plus a Sprint button.
	-- Crouch (toggle): Ctrl or C, gamepad B, phone Crouch button.
	-- Roll (GTA 5): Space while aiming a gun (gamepad L2 + A, phone Roll button), toward the way you're moving.
	Movement = {
		WalkSpeed = 8,
		JogSpeed = 14,
		SprintSpeed = 20,
		AimSprintSpeed = 12, -- aiming + sprint key: side run only (forward/back stay at the aim walk)
		CrouchSpeed = 4,
		CrouchCameraDrop = 1.3, -- camera sits this much lower while crouched
		RollSpeed = 17, -- studs/s during a roll (aim + Space)
		RollCooldown = 0.5, -- seconds after a roll before the next one
		FirstPersonRollCamera = true, -- in first person the view tumbles with the body through a roll
		Acceleration = 40, -- studs/s per second when speeding up (slowing down is 2x)
	},

	Weapons = {
		-- everyone gets these on join (put in their inventory, Server/Inventory), and spawns
		-- holding EquipOnSpawn
		DefaultLoadout = { "CarbineRifle" },
		EquipOnSpawn = "CarbineRifle",
		-- true: on-screen weapon state (Client/WeaponDebug) + "[Weapons]" / "[GunModel]" lines
		-- in Output, for chasing equip bugs
		Debug = false,
		-- extra weapons in Studio play tests only. Empty: Bat, Pistol, SMG and Shotgun have no
		-- models or animations yet, so keys 1-4 equipped invisible weapons and left the rifle
		-- on the back (looked like the rifle couldn't be equipped). Add them back once they have art.
		StudioLoadout = {},
		-- guns are shown at this scale (the carbine is exported at 3.6 studs per meter, which
		-- reads small next to chunky R15 bodies). The rifle animations (art/anim/gun.py
		-- GUN_SCALE) are solved for it, so change both together.
		GunScale = 1.7,
		-- damage multiplier per body part hit, for weapons without their own BodyDamage table
		-- (each weapon file in Shared/Weapons/Defs can override any part)
		BodyDamage = {
			Head = 2,
			UpperTorso = 1,
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
		-- Lag compensation (server, Server/Weapons/LagComp): hits on players are checked where
		-- the shooter saw them. Rewind = shooter's ping + Interpolation, never more than
		-- MaxRewind (so lag-switching can't reach further back). Walls are never rewound.
		LagComp = {
			Rate = 20, -- hitbox snapshots per second
			History = 0.6, -- seconds kept
			Interpolation = 0.05, -- seconds Roblox smooths other players on your screen
			MaxRewind = 0.25,
			Debug = false, -- Studio: show the rewound hitboxes for each shot
		},
		AimFieldOfView = 55, -- camera zooms in a little while aiming (normal is 70)
		LowerNearWalls = 2.4, -- studs: closer than this to a wall, the gun points down
		-- GTA rifle stance: while aiming, the hips and legs turn this many degrees right of the
		-- aim (the chest turns 48), so the whole body is bladed instead of only the chest twisting
		AimStance = { Still = 38, Moving = 20 },
		-- aiming standing still, the feet stay planted as you turn and take a turn step once the
		-- body is Turn degrees off them (or Settle degrees once the aim stops moving)
		AimStep = { Turn = 40, Settle = 14 },
		-- number keys pick a wheel slot (GTA-style wheel UI comes later)
		SlotKeys = { "Melee", "Pistol", "SMG", "Shotgun", "Rifle" },
	},

	-- Inventory (N opens it; Client/Inventory, Server/Inventory). Weights are kg; every item's
	-- own weight is in its config (Shared/Items: weapons in Weapons/Defs, the vest in Armor).
	Inventory = {
		-- grids (cells); items cover Cells = wide x tall of them (Shared/Items)
		Cols = 5, -- main inventory: 5 x 14
		Rows = 14,
		MaxWeight = 30,
		BackpackCols = 4, -- backpack: 4 x 4
		BackpackRows = 4,
		BackpackMaxWeight = 10,
		-- quick slots under the character (keys 1-3, the bar at the bottom of the screen): any
		-- item, one per slot; a gun there is drawn / put away with its key. They count toward
		-- MaxWeight. Config.Weapons.DefaultLoadout's weapons start in them.
		QuickSlots = 3,
		-- everyone starts with these (after Config.Weapons.DefaultLoadout's weapons)
		StartingItems = {
			{ Id = "Mead", Count = 1 },
			{ Id = "Chaser", Count = 1 },
			{ Id = "FirstAidKit", Count = 1 },
		},
		StartingArmor = "ArmorVest", -- worn from the start (the Armor slot)
		GroundRange = 8, -- studs: dropped items this close show under Ground
		PickupRange = 12, -- studs: the server refuses pickups further than this
		DroppedLifetime = 600, -- seconds before a dropped item disappears
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
		-- true: everyone gets the plain blocky R15 body (Dev wants the blocky, Minecraft-like
		-- look): avatar body packages are dropped and every body is the default size, which
		-- is also the rig the gun / vest animations are solved for. Clothes, skin colour,
		-- face, head, hair and accessories stay the player's own. false: their own body,
		-- sizes clamped by the limits below.
		Blocky = true,
		HeightMin = 0.9,
		HeightMax = 1.05,
		WidthMin = 0.8,
		WidthMax = 1.0,
		HeadMin = 0.95,
		HeadMax = 1.0,
		BodyTypeMax = 0.3, -- 0 = classic blocky proportions, 1 = full Rthro
		ProportionMax = 0.0,
	},

	-- Money (Server/Money): every player has Cash (wallet) and Bank, shown next to the radar.
	Money = {
		StartCash = 500,
		StartBank = 5000,
		-- keep balances between sessions (DataStore). Studio needs "Enable Studio Access
		-- to API Services" on, otherwise it just warns and starts everyone fresh.
		Save = true,
		DataStoreName = "Money_v1",
		AutosaveSeconds = 120,
	},

	-- Player IDs + overhead name tags (Server/PlayerIds, Client/NameTags).
	-- TUID: short ID handed out on join, counts up per server (1, 2, 3...), never reused
	-- in that server. StaticUID: permanent per account, from a global counter in a
	-- DataStore, the same every time they join.
	PlayerIds = {
		DataStoreName = "PlayerIds_v1",
		FirstStaticUID = 1, -- the first account ever to join gets this number
		-- tags above other players' heads
		TagMaxDistance = 40, -- studs; tags fade out over the last FadeStuds
		TagFadeStuds = 10,
		ShowOwnTag = false, -- true: you see your own tag too (handy for solo testing)
	},

	-- In-game clock (Server/GameClock + Shared/GameTime): drives Lighting.ClockTime and the
	-- time/date on the HUD. GTA style: one game day = 48 real minutes (1 game minute = 2 s).
	Time = {
		DayMinutes = 48, -- real minutes per in-game day
		StartHour = 9, -- in-game hour when a server starts
		-- the in-game date starts on the server's real (UTC) date and then counts game days
		DriveLighting = true, -- false: HUD clock still runs, but the sky stays as set in Studio
	},
}

return Config
