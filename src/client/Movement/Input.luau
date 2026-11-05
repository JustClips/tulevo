--[[
	Movement inputs, so moves ask for actions instead of keys.
		Input.isDown("Sprint")  -> boolean
		Input.analog()          -> true on gamepad / touch (sticks choose their own pace)

	Sprint: hold Shift, click the left stick (toggle), or the Sprint button on phones (toggle).
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
	},
}

local held: { [string]: boolean } = {}
local toggled: { [string]: boolean } = {}
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
		ContextActionService:SetPosition(`Move_{name}`, UDim2.new(1, -170, 1, -90))
	end
end

local function refresh()
	local t = UserInputService:GetLastInputType()
	analog = t == Enum.UserInputType.Touch or t.Name:sub(1, 7) == "Gamepad"
end
UserInputService.LastInputTypeChanged:Connect(refresh)
refresh()

function Input.isDown(name: string): boolean
	return held[name] == true or toggled[name] == true
end

-- Turn a toggled action off (e.g. sprint stops when you stop moving).
function Input.release(name: string)
	toggled[name] = false
end

function Input.analog(): boolean
	return analog
end

return Input
