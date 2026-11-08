--[[
	Driving inputs, read every physics step while you're in the driver's seat.
		Input.read() -> { Throttle = -1..1, Steer = -1..1, Handbrake = bool, Wheelie = bool }

	Keyboard: W/S (or arrows) gas and brake/reverse, A/D steer, Space handbrake.
	Gamepad: RT gas, LT brake/reverse, left stick steer, RB (or A) handbrake.
	Phones: the move stick (up = gas, down = brake/reverse, sideways = steer) + Brake button.
	F / gamepad Y / phone Exit button gets out (Vehicles/init binds that).
	Bikes: wheelie = Ctrl (gamepad: left stick pulled back, phones: Wheelie button).
]]

local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")

local Input = {}

local PRIORITY = Enum.ContextActionPriority.High.Value + 10 -- above the jump key, so Space doesn't jump out

local handbrake = false
local wheelieButton = false -- phone button / bound Ctrl (bikes)
local controls = nil -- Roblox's ControlModule, only used for the phone stick

local function key(...): boolean
	for _, k in { ... } do
		if UserInputService:IsKeyDown(k) then
			return true
		end
	end
	return false
end

local function deadzone(x: number): number
	return if math.abs(x) < 0.15 then 0 else x
end

-- Keys and sticks are read directly, so driving never waits on Roblox's PlayerModule.
local function moveVector(): Vector3
	local x, z = 0, 0
	if key(Enum.KeyCode.W, Enum.KeyCode.Up) then
		z -= 1
	end
	if key(Enum.KeyCode.S, Enum.KeyCode.Down) then
		z += 1
	end
	if key(Enum.KeyCode.D, Enum.KeyCode.Right) then
		x += 1
	end
	if key(Enum.KeyCode.A, Enum.KeyCode.Left) then
		x -= 1
	end
	if x ~= 0 or z ~= 0 then
		return Vector3.new(x, 0, z)
	end
	if UserInputService.GamepadEnabled then
		for _, state in UserInputService:GetGamepadState(Enum.UserInputType.Gamepad1) do
			if state.KeyCode == Enum.KeyCode.Thumbstick1 then
				local p = state.Position
				if math.abs(p.X) > 0.15 or math.abs(p.Y) > 0.15 then
					return Vector3.new(deadzone(p.X), 0, -deadzone(p.Y))
				end
			end
		end
	end
	if UserInputService.TouchEnabled then
		if controls == nil then
			controls = false
			local scripts = Players.LocalPlayer:FindFirstChild("PlayerScripts")
			local module = scripts and scripts:FindFirstChild("PlayerModule")
			if module then
				local ok, pm = pcall(require, module)
				controls = ok and pm:GetControls() or false
			end
		end
		if controls then
			return controls:GetMoveVector()
		end
	end
	return Vector3.zero
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
	local wheelie = wheelieButton
		or key(Enum.KeyCode.LeftControl, Enum.KeyCode.RightControl)
		or (gamepad() and move.Z > 0.6) -- stick pulled back
	return {
		Throttle = math.clamp(throttle, -1, 1),
		Steer = math.clamp(move.X, -1, 1),
		Handbrake = handbrake,
		Wheelie = wheelie,
	}
end

-- Driving controls on/off (Vehicles/init calls this when you get in and out). opts.Wheelie: bikes.
function Input.bind(onExit: () -> (), opts: { Wheelie: boolean? }?)
	handbrake = false
	wheelieButton = false
	if opts and opts.Wheelie then
		-- Ctrl is bound too, so it doesn't crouch while riding
		ContextActionService:BindActionAtPriority("Vehicle_Wheelie", function(_, state)
			wheelieButton = state == Enum.UserInputState.Begin
			return Enum.ContextActionResult.Sink
		end, true, PRIORITY, Enum.KeyCode.LeftControl, Enum.KeyCode.RightControl)
		ContextActionService:SetTitle("Vehicle_Wheelie", "Wheelie")
		ContextActionService:SetPosition("Vehicle_Wheelie", UDim2.new(1, -95, 1, -285))
	end
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
	wheelieButton = false
	ContextActionService:UnbindAction("Vehicle_Wheelie")
	ContextActionService:UnbindAction("Vehicle_Handbrake")
	ContextActionService:UnbindAction("Vehicle_Exit")
end

return Input
