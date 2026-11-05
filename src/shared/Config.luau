-- Shared settings, readable from server and client:
-- require(game.ReplicatedStorage.Shared.Config)
local Config = {
	GameName = "Tulevo",

	-- On foot (GTA style), used by StarterPlayerScripts.Client.Movement.
	-- Keyboard: walk, hold Shift to sprint. Gamepad: stick pushed a little = walk, all the
	-- way = jog, click the left stick to sprint. Phones: same stick, plus a Sprint button.
	Movement = {
		WalkSpeed = 6,
		JogSpeed = 14,
		SprintSpeed = 20,
		Acceleration = 40, -- studs/s per second when speeding up (slowing down is 2x)
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
