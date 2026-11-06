-- iPhone-like motion for the phone screen:
--   app pages zoom out of their home icon and shrink back into it,
--   the home screen sinks back a little while an app is open,
--   icons settle in when the phone wakes.
-- All positions are in screen units (Theme), so it works at any phone size.
local TweenService = game:GetService("TweenService")

local Motion = {}

local OPEN = TweenInfo.new(0.42, Enum.EasingStyle.Quint, Enum.EasingDirection.Out)
local CLOSE = TweenInfo.new(0.36, Enum.EasingStyle.Quint, Enum.EasingDirection.Out)
local FADE_IN = TweenInfo.new(0.22, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
local SETTLE = TweenInfo.new(0.55, Enum.EasingStyle.Quint, Enum.EasingDirection.Out)

local function play(obj: Instance, info: TweenInfo, props)
	local tw = TweenService:Create(obj, info, props)
	tw:Play()
	return tw
end
Motion.play = play

-- where an icon is, inside `screen` (centre + width, in screen units)
function Motion.iconRect(icon: GuiObject?, screen: GuiObject, uiScale: number)
	if not icon or not icon.Parent or uiScale <= 0 then
		return nil
	end
	local rel = (icon.AbsolutePosition + icon.AbsoluteSize / 2 - screen.AbsolutePosition) / uiScale
	return { center = rel, width = icon.AbsoluteSize.X / uiScale }
end

-- page: full-screen GuiObject with a UIScale "Zoom" and a "Splash" cover in the app colour.
-- rect = the icon it grows out of (nil = grows from the middle).
function Motion.zoomIn(page: GuiObject, rect, screenSize: Vector2)
	local zoom = page:FindFirstChild("Zoom") :: UIScale
	local splash = page:FindFirstChild("Splash") :: GuiObject
	page.AnchorPoint = Vector2.new(0.5, 0.5)
	if rect then
		page.Position = UDim2.fromOffset(rect.center.X, rect.center.Y)
		zoom.Scale = rect.width / screenSize.X
	else
		page.Position = UDim2.fromScale(0.5, 0.5)
		zoom.Scale = 0.8
	end
	play(zoom, OPEN, { Scale = 1 })
	local tw = play(page, OPEN, { Position = UDim2.fromScale(0.5, 0.5) })
	-- the icon colour fades into the app, like iOS
	task.delay(0.12, function()
		if splash.Parent then
			play(splash, FADE_IN, { BackgroundTransparency = 1 })
			for _, d in splash:GetDescendants() do
				if d:IsA("ImageLabel") then
					play(d, FADE_IN, { ImageTransparency = 1 })
				end
			end
		end
	end)
	return tw
end

-- shrinks the page back into its icon; returns the tween (destroy the page when it ends)
function Motion.zoomOut(page: GuiObject, rect, screenSize: Vector2)
	local zoom = page:FindFirstChild("Zoom") :: UIScale
	local splash = page:FindFirstChild("Splash") :: GuiObject
	play(splash, TweenInfo.new(0.14), { BackgroundTransparency = 0 })
	for _, d in splash:GetDescendants() do
		if d:IsA("ImageLabel") then
			play(d, TweenInfo.new(0.14), { ImageTransparency = 0 })
		end
	end
	if rect then
		play(zoom, CLOSE, { Scale = rect.width / screenSize.X })
		return play(page, CLOSE, { Position = UDim2.fromOffset(rect.center.X, rect.center.Y) })
	end
	return play(zoom, CLOSE, { Scale = 0.8 })
end

-- home screen sinks back (app open) or comes forward again
function Motion.homeBack(homeScale: UIScale, back: boolean)
	play(homeScale, if back then OPEN else CLOSE, { Scale = if back then 0.92 else 1 })
end

-- phone woke up: icons settle in from slightly bigger, like unlocking an iPhone
function Motion.wake(homeScale: UIScale)
	homeScale.Scale = 1.12
	play(homeScale, SETTLE, { Scale = 1 })
end

return Motion
