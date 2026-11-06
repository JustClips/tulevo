-- The Dynamic Island. Island.show(text, seconds) grows the pill, shows the text, and
-- shrinks it back, like a notification on a real phone. Apps can use it via Phone.notify.
local TweenService = game:GetService("TweenService")

local Island = {}

local SMALL = UDim2.fromOffset(92, 27)
local BIG_H = 34

local pill: Frame
local text: TextLabel
local token = 0

function Island.attach(frame: Frame)
	pill = frame
	text = frame:FindFirstChild("Text") :: TextLabel
end

local function tween(obj: Instance, t: number, props, style: Enum.EasingStyle?)
	local tw = TweenService:Create(obj, TweenInfo.new(t, style or Enum.EasingStyle.Quint, Enum.EasingDirection.Out), props)
	tw:Play()
	return tw
end

function Island.show(message: string, seconds: number?)
	if not pill then
		return
	end
	token += 1
	local mine = token
	text.Text = message
	local width = math.clamp(text.TextBounds.X + 70, 150, 236)
	tween(pill, 0.38, { Size = UDim2.fromOffset(width, BIG_H) }, Enum.EasingStyle.Back)
	tween(text, 0.25, { TextTransparency = 0 })
	task.delay(seconds or 2.5, function()
		if mine ~= token then
			return
		end
		tween(text, 0.15, { TextTransparency = 1 })
		tween(pill, 0.35, { Size = SMALL })
	end)
end

-- back to the small pill at once (when the phone closes)
function Island.reset()
	if not pill then
		return
	end
	token += 1
	pill.Size = SMALL
	text.TextTransparency = 1
end

return Island
