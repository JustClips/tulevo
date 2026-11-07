-- iPhone-like motion for the phone screen:
--   an app opens as a rounded card that grows out of its home icon (icon colour fading
--   into the app) and shrinks back into the same icon square when you go home,
--   the home screen sinks back a little while an app is open,
--   icons settle in when the phone wakes.
-- The card is a CanvasGroup only while it moves (rounded clipping + fade); once the app
-- is open the page goes back to a plain frame so text stays sharp.
-- All positions are in screen units (Theme), so it works at any phone size.
local TweenService = game:GetService("TweenService")

local Theme = require(script.Parent.Theme)

local Motion = {}

local OPEN = TweenInfo.new(0.46, Enum.EasingStyle.Quint, Enum.EasingDirection.Out)
local CLOSE = TweenInfo.new(0.4, Enum.EasingStyle.Quint, Enum.EasingDirection.Out)
local SPLASH_OUT = TweenInfo.new(0.24, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
local SPLASH_IN = TweenInfo.new(0.16, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
local SETTLE = TweenInfo.new(0.55, Enum.EasingStyle.Quint, Enum.EasingDirection.Out)
local NO_ICON_SCALE = 0.86 -- an app without a home icon grows from / shrinks to this

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

-- the moving card a page sits in while it zooms (nil when the page is at rest)
local function cardOf(page: GuiObject): CanvasGroup?
	local p = page.Parent
	if p and p:IsA("CanvasGroup") and p.Name == "AppCard" then
		return p
	end
	return nil
end

-- icon-coloured cover with the app's glyph, like the icon on the home screen
local function makeSplash(card: Instance, look)
	local splash = Instance.new("Frame")
	splash.Name = "Splash"
	splash.Size = UDim2.fromScale(1, 1)
	splash.BackgroundColor3 = look.Color or Theme.Colors.Page
	splash.BorderSizePixel = 0
	splash.ZIndex = 50
	local grad = Instance.new("UIGradient")
	grad.Rotation = 90
	grad.Color = ColorSequence.new(Color3.new(1, 1, 1), Color3.fromRGB(200, 200, 200))
	grad.Parent = splash
	if look.Icon then
		local s = look.IconScale or 0.62
		local img = Instance.new("ImageLabel")
		img.BackgroundTransparency = 1
		img.AnchorPoint = Vector2.new(0.5, 0.5)
		img.Position = UDim2.fromScale(0.5, 0.5)
		img.Size = UDim2.fromScale(s, s)
		img.SizeConstraint = Enum.SizeConstraint.RelativeXX
		img.Image = look.Icon
		img.ZIndex = 51
		img.Parent = splash
	end
	splash.Parent = card
	return splash
end

local function setSplash(splash: GuiObject, info: TweenInfo, t: number)
	play(splash, info, { BackgroundTransparency = t })
	for _, d in splash:GetDescendants() do
		if d:IsA("ImageLabel") then
			play(d, info, { ImageTransparency = t })
		end
	end
end

-- puts the page inside a fresh card covering the whole screen
local function wrap(page: GuiObject, screenSize: Vector2, look)
	local card = Instance.new("CanvasGroup")
	card.Name = "AppCard"
	card.AnchorPoint = Vector2.new(0.5, 0.5)
	card.Position = UDim2.fromScale(0.5, 0.5)
	card.Size = UDim2.fromOffset(screenSize.X, screenSize.Y)
	card.BackgroundTransparency = 1
	card.BorderSizePixel = 0
	card.ZIndex = page.ZIndex
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, Theme.ScreenRadius)
	corner.Parent = card
	card.Parent = page.Parent
	-- the page keeps its full size and is scaled down to the card's width
	page.AnchorPoint = Vector2.new(0.5, 0.5)
	page.Position = UDim2.fromScale(0.5, 0.5)
	page.Size = UDim2.fromOffset(screenSize.X, screenSize.Y)
	page.Parent = card
	local splash = makeSplash(card, look)
	splash.BackgroundTransparency = 1
	return card, corner, splash
end

-- the card reached full screen: page back to a plain full-screen frame
local function unwrap(page: GuiObject, card: CanvasGroup)
	page.Parent = card.Parent
	page.AnchorPoint = Vector2.new(0, 0)
	page.Position = UDim2.new()
	page.Size = UDim2.fromScale(1, 1)
	local zoom = page:FindFirstChild("Zoom") :: UIScale?
	if zoom then
		zoom.Scale = 1
	end
	card:Destroy()
end

-- tweens card + page together (same TweenInfo, so the page width always matches the card)
local function moveCard(
	card: CanvasGroup,
	page: GuiObject,
	info: TweenInfo,
	pos: UDim2,
	size: Vector2,
	radius: number,
	screenSize: Vector2
)
	local zoom = page:FindFirstChild("Zoom") :: UIScale
	play(zoom, info, { Scale = size.X / screenSize.X })
	play(card:FindFirstChildOfClass("UICorner") :: UICorner, info, { CornerRadius = UDim.new(0, radius) })
	return play(card, info, { Position = pos, Size = UDim2.fromOffset(size.X, size.Y) })
end

-- page: full-screen GuiObject with a UIScale "Zoom". rect = the icon it grows out of
-- (nil = grows from the middle). look = { Color, Icon, IconScale } of that icon.
-- Returns the tween; its Completed state is Completed only if the zoom finished.
function Motion.zoomIn(page: GuiObject, rect, screenSize: Vector2, look)
	local card, corner, splash = wrap(page, screenSize, look or {})
	local zoom = page:FindFirstChild("Zoom") :: UIScale
	if rect then
		card.Position = UDim2.fromOffset(rect.center.X, rect.center.Y)
		card.Size = UDim2.fromOffset(rect.width, rect.width)
		corner.CornerRadius = UDim.new(0, Theme.IconRadius * rect.width / Theme.IconSize)
		zoom.Scale = rect.width / screenSize.X
		setSplash(splash, TweenInfo.new(0), 0)
		-- the icon colour melts into the app, like iOS
		task.delay(0.06, function()
			if splash.Parent then
				setSplash(splash, SPLASH_OUT, 1)
			end
		end)
	else
		local s = screenSize * NO_ICON_SCALE
		card.Size = UDim2.fromOffset(s.X, s.Y)
		zoom.Scale = NO_ICON_SCALE
		card.GroupTransparency = 1
		play(card, SPLASH_OUT, { GroupTransparency = 0 })
	end
	local tw = moveCard(card, page, OPEN, UDim2.fromScale(0.5, 0.5), screenSize, Theme.ScreenRadius, screenSize)
	tw.Completed:Connect(function(state)
		if state == Enum.PlaybackState.Completed and cardOf(page) == card then
			unwrap(page, card)
		end
	end)
	return tw
end

-- shrinks the page back into its icon square; returns the tween (call Motion.discard
-- on the page when it ends)
function Motion.zoomOut(page: GuiObject, rect, screenSize: Vector2, look)
	local card = cardOf(page)
	local splash
	if card then
		-- still opening: turn around from where it is now
		splash = card:FindFirstChild("Splash") :: GuiObject
	else
		local newCard, _corner, newSplash = wrap(page, screenSize, look or {})
		card, splash = newCard, newSplash
	end
	if rect then
		setSplash(splash, SPLASH_IN, 0)
		local r = Theme.IconRadius * rect.width / Theme.IconSize
		return moveCard(
			card,
			page,
			CLOSE,
			UDim2.fromOffset(rect.center.X, rect.center.Y),
			Vector2.new(rect.width, rect.width),
			r,
			screenSize
		)
	end
	play(card, SPLASH_IN, { GroupTransparency = 1 })
	return moveCard(
		card,
		page,
		CLOSE,
		UDim2.fromScale(0.5, 0.5),
		screenSize * NO_ICON_SCALE,
		Theme.ScreenRadius,
		screenSize
	)
end

-- removes a page and the card it may still be moving in
function Motion.discard(page: GuiObject)
	local card = cardOf(page)
	if card then
		card:Destroy()
	else
		page:Destroy()
	end
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
