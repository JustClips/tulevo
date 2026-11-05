--[[
	Driving inputs, read every physics step while you're in the driver's seat.
		Input.read() -> { Throttle = -1..1, Steer = -1..1, Handbrake = bool }

	Keyboard: W/S (or arrows) gas and brake/reverse, A/D steer, Space handbrake.
	Gamepad: RT gas, LT brake/reverse, left stick steer, RB (or A) handbrake.
	Phones: the move stick (up = gas, down = brake/reverse, sideways = steer) + Brake button.
	F / gamepad Y / phone Exit button gets out (Vehicles/init binds that).
]]

local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")

local Input = {}

local PRIORITY = Enum.ContextActionPriority.High.Value + 10 -- above the jump key, so Space doesn't jump out

local handbrake = false
local controls = nil

local function moveVector(): Vector3
	if not controls then
		local ok, module = pcall(function()
			return require(Players.LocalPlayer:WaitForChild("PlayerScripts"):WaitForChild("PlayerModule"))
		end)
		controls = ok and module:GetControls() or false
	end
	return if controls then controls:GetMoveVector() else Vector3.zero
end

local function gamepad(): boolean
	return UserInputService:GetLastInputType().Name:sub(1, 7) == "Gamepad"
end

function Input.read()
	local move = moveVector()
	local throttle = -move.Z
	if gamepad() then
		local rt, lt = 0, 0
		for _, state in UserInputService:GetGamepadState(Enum.UserInputType.Gamepad1) do
			if state.KeyCode == Enum.KeyCode.ButtonR2 then
				rt = state.Position.Z
			elseif state.KeyCode == Enum.KeyCode.ButtonL2 then
				lt = state.Position.Z
			end
		end
		throttle = rt - lt -- GTA style: triggers drive, the stick only steers
	end
	return {
		Throttle = math.clamp(throttle, -1, 1),
		Steer = math.clamp(move.X, -1, 1),
		Handbrake = handbrake,
	}
end

-- Driving controls on/off (Vehicles/init calls this when you get in and out).
function Input.bind(onExit: () -> ())
	handbrake = false
	ContextActionService:BindActionAtPriority("Vehicle_Handbrake", function(_, state)
		handbrake = state == Enum.UserInputState.Begin
		return Enum.ContextActionResult.Sink
	end, true, PRIORITY, Enum.KeyCode.Space, Enum.KeyCode.ButtonR1, Enum.KeyCode.ButtonA)
	ContextActionService:SetTitle("Vehicle_Handbrake", "Brake")
	ContextActionService:SetPosition("Vehicle_Handbrake", UDim2.new(1, -95, 1, -210))

	ContextActionService:BindActionAtPriority("Vehicle_Exit", function(_, state)
		if state == Enum.UserInputState.Begin then
			onExit()
		end
		return Enum.ContextActionResult.Sink
	end, true, PRIORITY, Enum.KeyCode.F, Enum.KeyCode.ButtonY)
	ContextActionService:SetTitle("Vehicle_Exit", "Exit")
	ContextActionService:SetPosition("Vehicle_Exit", UDim2.new(1, -170, 1, -210))
end

function Input.unbind()
	handbrake = false
	ContextActionService:UnbindAction("Vehicle_Handbrake")
	ContextActionService:UnbindAction("Vehicle_Exit")
end

return Input
