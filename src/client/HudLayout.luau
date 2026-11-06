-- Where the radar and health bar go, and how big, for the current screen.
--   Desktop/console: bottom-left (radar above the health bar).
--   Phones/tablets:  top-left, under Roblox's top buttons (radar, then the bar),
--                    so the left thumbstick area stays free.
-- Everything is scaled with the screen height (UIScale), so a phone gets a
-- smaller radar instead of one that covers half the screen.
-- HudLayout.get() -> { scale, touch }; HudLayout.Changed fires on resize.
local UserInputService = game:GetService("UserInputService")

local HudLayout = {}

local REF_HEIGHT = 900 -- screen height (px) where scale = 1
local MIN_SCALE, MAX_SCALE = 0.65, 1

local changed = Instance.new("BindableEvent")
HudLayout.Changed = changed.Event

function HudLayout.get()
	local cam = workspace.CurrentCamera
	local h = if cam then cam.ViewportSize.Y else REF_HEIGHT
	return {
		scale = math.clamp(h / REF_HEIGHT, MIN_SCALE, MAX_SCALE),
		touch = UserInputService.TouchEnabled and not UserInputService.KeyboardEnabled,
	}
end

local function watch(cam: Camera?)
	if cam then
		cam:GetPropertyChangedSignal("ViewportSize"):Connect(function()
			changed:Fire()
		end)
	end
end
watch(workspace.CurrentCamera)
workspace:GetPropertyChangedSignal("CurrentCamera"):Connect(function()
	watch(workspace.CurrentCamera)
	changed:Fire()
end)

return HudLayout
