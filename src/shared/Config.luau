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
		-- false: walk/run/sprint/strafe/crouch clips always play at their normal speed (Dev's
		-- pick, 2026-11-06; feet slide a bit). true: playback follows movement speed so the feet
		-- match the ground (up to each gait's MaxRate).
		AnimRateFollowsSpeed = false,
		CrouchSpeed = 4,
		CrouchCameraDrop = 1.3, -- camera sits this much lower while crouched
		RollSpeed = 17, -- studs/s during a roll (aim + Space)
		RollCooldown = 0.5, -- seconds after a roll before the next one
		FirstPersonRollCamera = true, -- in first person the view tumbles with the body through a roll
		Acceleration = 40, -- studs/s per second when speeding up (slowing down is 2x)
		-- seconds every move/animation change cross-fades over (walk <-> run <-> sprint, into and
		-- out of jumps, rolls, stops), instead of switching instantly
		BlendTime = 0.2,
		-- starting from standing plays a lean-in first step, letting go while walking/running
		-- plays 1-3 slowing steps (Moves/StartStep, Moves/StopStep)
		StartStopSteps = true,
	},

	-- PC mouse look, GTA 5 style (Client/Movement/MouseLook). The mouse always turns the camera
	-- (cursor hidden, no right-drag); menus or holding Left Alt bring the cursor back. Input is
	-- raw 1:1 (no acceleration or smoothing) and up/down turns as fast as left/right. Roblox's
	-- own Esc-menu sensitivity and invert still apply on top. Tune live: F8 > Camera.
	Camera = {
		MouseLook = true, -- false: Roblox default (right-drag to turn) unless a gun is out
		Sensitivity = 1, -- on foot
		AimSensitivity = 1, -- while aiming (right click), times the zoom scale below
		VehicleSensitivity = 1, -- driving / riding
		-- aiming: also scale by the zoom, so the world under the crosshair moves at the same speed
		-- zoomed in (Weapons.AimFieldOfView) as at the normal field of view
		AimFovScale = true,
		BaseFieldOfView = 70,
		EqualAxes = true, -- up/down as fast as left/right (Roblox normally turns up/down 23% slower)
		FreeCursorKey = Enum.KeyCode.LeftAlt, -- hold to get the cursor back
	},

	Weapons = {
		-- hold Q / E to lean (gun or not): the upper body tilts this many degrees round the aim
		-- (the server moves the shot origin with it, so you can shoot round a corner)
		LeanAngle = 25,
		-- false: no body posing at all (aim chest lock, stance, lean; Client/Weapons/GunPose).
		-- A kill switch in case the joint posing ever misbehaves.
		BodyPose = true,
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
		-- shot VFX (Client/Weapons/Effects; sprites rendered in Blender, art/blender/weapons)
		Fx = {
			FlashTime = 0.045, -- seconds the flash is up (GTA: a frame or two)
			FlashSize = 1.0, -- studs per render unit: the plume is ~0.8-1.1 of them long
			FlashBrightness = 2.5,
			StarSize = 1.1, -- the down-the-barrel star (shows only when looking along the barrel)
			LightRange = 9,
			LightBrightness = 2.5,
			SmokeSize = 1.4, -- studs, when the puff has spread
			SmokeOpacity = 0.35,
			-- tracer: a thin streak flying from the muzzle to the hit
			TracerChance = 1, -- share of shots that draw one (GTA shows nearly every one)
			TracerSpeed = 1100, -- studs per second
			TracerLength = 12, -- studs of streak
			TracerStart = 1.2, -- studs past the muzzle it starts (clear of the flash)
			TracerPixels = 4, -- on-screen width of the streak's sprite (the bright core is ~1/3)
			TracerMinWidth = 0.05,
			TracerBrightness = 3,
		},
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
		-- Gun sounds (Client/Weapons/GunAudio, files from tools/gun_sounds.py). Volumes are 0-1+,
		-- distances in studs.
		Sound = {
			Enabled = true,
			Volume = 1, -- master for every gun sound
			PitchJitter = 0.03, -- each shot/impact is up to 3% higher or lower so autofire isn't a loop
			OwnShot = 1.8, -- your own gun
			-- someone else's gun: Shot is the loudness at ShotRef studs, then it falls off with
			-- distance ^ ShotFalloff. Closer than NearRange you hear the close-up shot, up to
			-- DistantRange the distant one, then the far pop; nothing past MaxRange.
			Shot = 2,
			ShotRef = 15,
			ShotFalloff = 0.85,
			NearRange = 70,
			DistantRange = 260,
			MaxRange = 900,
			DistantBoost = 1.2, -- the distant / far files are duller, so they get a little extra
			FarBoost = 1.6,
			SpeedOfSound = 1225, -- studs/s (343 m/s): far shots are heard after their bullets land
			-- bullets passing you: crack within CrackRadius (full loudness at CrackRef), whizz within WhizRadius
			Crack = 1.4,
			CrackRef = 4,
			CrackRadius = 30,
			Whiz = 0.9,
			WhizRadius = 7,
			-- bullets hitting things: full loudness at ImpactRef, unheard past ImpactRange
			Impact = 1.1,
			ImpactRef = 8,
			ImpactRange = 170,
			Body = 1.8, -- a bullet hitting someone else
			BodyOnYou = 1.5, -- a bullet hitting you
			Ricochet = 0.4, -- of the impact's loudness
			RicochetChance = 0, -- per hit on concrete / metal (0 = off; Dev disliked them)
			Reload = 1.3, -- reload sounds (Server/Weapons/GunModel), heard up to ReloadRange studs
			ReloadRange = 60,
		},
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

	-- Gangs (Server/Gangs): one Team each, and each has its own neighborhood with a court
	-- spawn (City/<Id>Spawn, attribute Gang = Id, from tools/build_city_map.py). Members spawn
	-- there; everyone else (Civilians) spawns at the main spawn plaza. Original names only.
	Gangs = {
		{ Id = "RedCrowns", Name = "Red Crowns", Color = Color3.fromRGB(200, 30, 36) },
		{ Id = "Vipers", Name = "Vipers", Color = Color3.fromRGB(240, 196, 30) },
		{ Id = "GroveKings", Name = "Grove Kings", Color = Color3.fromRGB(40, 160, 70) },
	},

	-- Cars (docs/vehicles.md). Get in with F (gamepad Y, tap the prompt on phones), out with F again.
	-- W/S or triggers = gas/brake/reverse, A/D or stick = steer, Space / RB = handbrake.
	Vehicles = {
		EnterDistance = 8, -- studs from the driver's door
		-- parked next to the spawn on start; Offset from the spawn, Yaw 0 = facing north (-Z)
		TestCars = {
			-- spawn plaza: between the spawn and the avenue, clear of the kiosk and lamps
			{ Id = "Sedan", Offset = Vector3.new(9, 0, 16), Yaw = 0 },
			{ Id = "Hypercar", Offset = Vector3.new(-9, 0, 16), Yaw = 0 },
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
		ShowOwnTag = true, -- true: you see your own tag too (handy for solo testing)
	},

	-- Knocked down instead of dying (Server/Knocked + Client/Knocked): health 0 = ragdoll on the
	-- floor with the "ВЫ РАНЕНЫ" screen. "Ожидать помощи" stays down, "Потерять сознание"
	-- respawns.
	Knocked = {
		Enabled = true, -- false: old behaviour (die and respawn after RespawnTime)
		GiveUpDelay = 1.5, -- seconds before "Потерять сознание" works (no accidental clicks)
		ReviveHealth = 10, -- health after being picked up
		ReviveHold = 4, -- seconds another player holds E ("Поднять") next to the body
		ReviveDistance = 7, -- studs
		FallPush = 9, -- random sideways push when falling (studs/s), so bodies land differently
		CameraMinZoom = 9, -- camera pulled out of first person while lying down
	},

	-- Debug panel (Server/DebugPanel + Client/DebugPanel): F8 opens it for these accounts
	-- (and for anyone in Studio play tests). The server checks every action again, so
	-- nobody else can use it even with an exploit.
	Debug = {
		Admins = { 347852675, 822623546 },
		AllowInStudio = true,
		Key = Enum.KeyCode.F8,
	},

	-- Server checks (Server/Guard + Server/MovementGuard, docs/server-checks.md). The server
	-- decides damage, money and items; these limits catch clients that lie about movement.
	AntiCheat = {
		Debug = false, -- true: print every rejected request
		-- on foot: horizontal studs/s over a CheckEvery window (sprint is 20, a roll 17)
		MaxFootSpeed = 45,
		TeleportStuds = 80, -- one window moving further than this = pulled back right away
		CheckEvery = 0.5, -- seconds between movement checks
		Strikes = 2, -- windows in a row over MaxFootSpeed before pulling back
		SpawnGrace = 2, -- seconds after spawning / a server teleport with no checks
		KnockedDrift = 12, -- studs a knocked body may slide from where it fell
		CarSpeedFactor = 1.6, -- driven cars may go this many times their MaxSpeed (crashes, ramps)
	},

	-- In-game clock (Server/GameClock + Shared/GameTime): drives Lighting.ClockTime and the
	-- time/date on the HUD. GTA style: one game day = 48 real minutes (1 game minute = 2 s).
	Time = {
		DayMinutes = 48, -- real minutes per in-game day
		StartHour = 9, -- in-game hour when a server starts
		-- the in-game date starts on the server's real (UTC) date and then counts game days
		DriveLighting = true, -- false: HUD clock still runs, but the sky stays as set in Studio
	},

	-- Weather (Server/Weather + Client/Weather, docs/weather.md; also the F8 debug panel). The server picks the weather
	-- and everyone blends to it over FadeSeconds; clouds drift on the server clock, so every
	-- player sees the same sky. Admins (and anyone in a Studio play test) can type
	-- /weather clear | cloudy | rain | heavyrain | thunderstorm | auto  in chat.
	Weather = {
		Enabled = true,
		Start = "Clear", -- weather when a server starts
		Cycle = true, -- false: stays on Start until someone uses /weather
		MinMinutes = 6, -- real minutes each weather lasts (random in between)
		MaxMinutes = 14,
		-- how often each weather is picked by the cycle
		Chances = { Clear = 5, Cloudy = 3, Rain = 2, HeavyRain = 1, Thunderstorm = 1 },
		FadeSeconds = 30, -- seconds to blend from one weather into the next
		Admins = { 822623546, 347852675 }, -- user ids allowed to use /weather in live servers
		DriveSky = true, -- false: leave Lighting/Atmosphere as set in Studio (clouds and rain still run)
		-- clouds: direction they drift (x, z) and studs per second
		WindDirection = Vector2.new(1, 0.35),
		CloudSpeed = 9,
		RainVolume = 0.55, -- rain loop volume at full rain
		-- Thunderstorm lightning (Server/Weather picks strikes, Client/Weather/Lightning draws them)
		Lightning = {
			MinGap = 3, -- seconds between strikes (random in between)
			MaxGap = 11,
			SheetChance = 0.4, -- share of flashes that stay inside the clouds (no bolt)
			NearChance = 0.3, -- share of bolts that land near a player (NearMin-NearMax studs away)
			NearMin = 40,
			NearMax = 260,
			FarRadius = 1800, -- other bolts land anywhere this far round a player
			ShakeRadius = 220, -- bolts closer than this shake the camera and flash the screen
		},
	},

	-- City ambience (Client/Ambience.client, docs/ambience.md): distant traffic bed (day / night), crickets at
	-- night, and one-off distant sounds placed around you: birds (mornings, never in rain),
	-- dogs (more at night), sirens, car horns. Muffled under a roof. Volumes per layer:
	Ambience = {
		Enabled = true,
		Volume = 1, -- master
		DayTraffic = 0.17,
		NightTraffic = 0.13,
		Crickets = 0.1,
		Birds = 0.22,
		Dogs = 0.28,
		Sirens = 0.3,
		Horns = 0.22,
		-- average seconds between one-offs when they're at their most likely
		Every = { Birds = 9, Dogs = 50, Sirens = 75, Horns = 40 },
	},

	-- Item use sounds (Client/UseSounds): drinking, the first-aid kit... played on whoever uses
	-- the item, heard up to MaxDistance studs away.
	UseSounds = {
		Volume = 0.9,
		MaxDistance = 45,
	},

	-- Phone (Client/Phone, docs/phone.md). Opens with a GTA-style slide up from the bottom right.
	-- Apps are modules in Client/Phone/Apps.
	Phone = {
		Key = Enum.KeyCode.Up, -- on foot only; in a car the arrow keys still drive
		GamepadKey = Enum.KeyCode.DPadDown, -- D-pad up/left/right are quick slots
		ScreenHeight = 0.62, -- share of the screen height the phone takes (desktop)
		TouchScreenHeight = 0.8, -- phones are small, so the phone is bigger there
		OpenTime = 0.7, -- slow smooth slide up (Dev 2026-11-06: no shake)
		CloseTime = 0.55,
		SoundVolume = 0.6, -- open / close sound (0 = off)
	},
}

return Config
