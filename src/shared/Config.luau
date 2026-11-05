-- Shared settings, readable from server and client:
-- require(game.ReplicatedStorage.Shared.Config)
local Config = {
	GameName = "Tulevo",

	-- On foot (GTA style): walk by default, hold Shift (keyboard) or click the left stick
	-- (gamepad) to run. Phones and gamepads get analog speed: push the stick a little to walk.
	WalkSpeed = 6,
	RunSpeed = 14,
}

return Config
