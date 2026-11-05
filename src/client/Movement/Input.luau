--[[
	Movement inputs, so moves ask for actions instead of keys.
		Input.isDown("Sprint")  -> boolean
		Input.analog()          -> true on gamepad / touch (sticks choose their own pace)

	Sprint: hold Shift, click the left stick (toggle), or the Sprint button on phones (toggle).
	Crouch: Ctrl or C, gamepad B, or the Crouch button on phones (all toggle).
	New moves add their action to ACTIONS.
]]

local ContextActionService = game:GetService("ContextActionService")
local UserInputService = game:GetService("UserInputService")

local Input = {}

local ACTIONS = {
	Sprint = {
		hold = { Enum.KeyCode.LeftShift, Enum.KeyCode.RightShift },
		toggle = { Enum.KeyCode.ButtonL3 },
		touchButton = "Sprint", -- shown on phones, works as a toggle
		touchPosition = UDim2.new(1, -170, 1, -90),
		cancels = { "Crouch" }, -- pressing Sprint stands you up
	},
	Crouch = {
		toggle = { Enum.KeyCode.LeftControl, Enum.KeyCode.C, Enum.KeyCode.ButtonB },
		touchButton = "Crouch",
		touchPosition = UDim2.new(1, -170, 1, -150),
		cancels = { "Sprint" }, -- pressing Crouch mid-sprint drops straight into the crouch
	},
}

local held: { [string]: boolean } = {}
local toggled: { [string]: boolean } = {}
-- Cancelled by another action: stays off (even with its key still held) until pressed again.
local suppressed: { [string]: boolean } = {}

local function cancel(name: string)
	toggled[name] = false
	suppressed[name] = true
end
local analog = false

local function isIn(list, key)
	return list and table.find(list, key) ~= nil
end

for name, a in ACTIONS do
	local keys = {}
	for _, k in a.hold or {} do
		table.insert(keys, k)
	end
	for _, k in a.toggle or {} do
		table.insert(keys, k)
	end
	ContextActionService:BindAction(`Move_{name}`, function(_, state, obj)
		local touch = obj.UserInputType == Enum.UserInputType.Touch
		if state == Enum.UserInputState.Begin then
			-- the newest press wins: it switches off the actions it cancels
			suppressed[name] = false
			for _, other in a.cancels or {} do
				cancel(other)
			end
		end
		if touch or isIn(a.toggle, obj.KeyCode) then
			if state == Enum.UserInputState.Begin then
				toggled[name] = not toggled[name]
			end
		elseif state == Enum.UserInputState.Begin then
			held[name] = true
		elseif state == Enum.UserInputState.End or state == Enum.UserInputState.Cancel then
			held[name] = false
		end
		return Enum.ContextActionResult.Pass
	end, a.touchButton ~= nil, table.unpack(keys))
	if a.touchButton then
		ContextActionService:SetTitle(`Move_{name}`, a.touchButton)
		ContextActionService:SetPosition(`Move_{name}`, a.touchPosition)
	end
end

local function refresh()
	local t = UserInputService:GetLastInputType()
	analog = t == Enum.UserInputType.Touch or t.Name:sub(1, 7) == "Gamepad"
end
UserInputService.LastInputTypeChanged:Connect(refresh)
refresh()

function Input.isDown(name: string): boolean
	return not suppressed[name] and (held[name] == true or toggled[name] == true)
end

-- Turn a toggled action off (e.g. sprint stops when you stop moving).
function Input.release(name: string)
	toggled[name] = false
end

function Input.analog(): boolean
	return analog
end

return Input
