-- Builds the phone itself: titanium body, side buttons, black glass, screen, Dynamic
-- Island, status bar and home bar. No behaviour here (see init.luau), only instances.
--
-- If art/phone made a ForgeGUI body picture (PhoneArt.Frame), that picture is the body and
-- the side buttons; the screen sits in its black screen hole (PhoneArt.Screen, 0-1 of the
-- picture). Without it the body is drawn from Frames.

local Theme = require(script.Parent.Theme)
local Art = require(script.Parent.PhoneArt)

local C = Theme.Colors
local Frame = {}

local function new(class: string, props: { [string]: any }, children: { Instance }?): any
	local inst = Instance.new(class)
	for k, v in props do
		if k ~= "Parent" then
			(inst :: any)[k] = v
		end
	end
	for _, child in children or {} do
		child.Parent = inst
	end
	if props.Parent then
		inst.Parent = props.Parent
	end
	return inst
end
Frame.new = new

local function corner(r: number)
	return new("UICorner", { CornerRadius = UDim.new(0, r) })
end
local function pill()
	return new("UICorner", { CornerRadius = UDim.new(1, 0) })
end
Frame.corner = corner

-- metal-looking vertical gradient for buttons and the band
local function metal(rotation: number?)
	return new("UIGradient", {
		Rotation = rotation or 0,
		Color = ColorSequence.new({
			ColorSequenceKeypoint.new(0, C.TitaniumDark),
			ColorSequenceKeypoint.new(0.35, C.TitaniumLight),
			ColorSequenceKeypoint.new(0.6, C.Titanium),
			ColorSequenceKeypoint.new(1, C.TitaniumDark),
		}),
	})
end

-- side button: x = which edge (-1 left, 1 right), y/h in units from the top
local function sideButton(parent: Instance, name: string, side: number, y: number, h: number)
	return new("TextButton", {
		Name = name,
		Parent = parent,
		Text = "",
		AutoButtonColor = false,
		AnchorPoint = Vector2.new(if side < 0 then 1 else 0, 0),
		Position = UDim2.new(if side < 0 then 0 else 1, if side < 0 then 1 else -1, 0, y),
		Size = UDim2.fromOffset(4, h),
		BackgroundColor3 = C.Titanium,
		BorderSizePixel = 0,
		ZIndex = 0,
	}, { new("UICorner", { CornerRadius = UDim.new(0, 2) }), metal(0) })
end

-- the black pill at the top of the screen; it can grow for notifications (Island.luau)
local function island(parent: Instance)
	local pillFrame = new("Frame", {
		Name = "Island",
		Parent = parent,
		AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.fromOffset(0, 11),
		Size = UDim2.fromOffset(92, 27),
		BackgroundColor3 = C.Island,
		BorderSizePixel = 0,
		ZIndex = 50,
	}, { pill() })
	-- front camera lens on the right end of the pill
	new("Frame", {
		Name = "Lens",
		Parent = pillFrame,
		AnchorPoint = Vector2.new(1, 0.5),
		Position = UDim2.new(1, -9, 0.5, 0),
		Size = UDim2.fromOffset(10, 10),
		BackgroundColor3 = Color3.fromRGB(14, 16, 26),
		ZIndex = 51,
	}, {
		pill(),
		new("UIStroke", { Color = Color3.fromRGB(30, 34, 52), Thickness = 1 }),
		new("Frame", {
			AnchorPoint = Vector2.new(0.5, 0.5),
			Position = UDim2.fromScale(0.38, 0.38),
			Size = UDim2.fromOffset(3, 3),
			BackgroundColor3 = Color3.fromRGB(70, 80, 130),
			BackgroundTransparency = 0.3,
			ZIndex = 52,
		}, { pill() }),
	})
	-- text shown when the island grows (Island.show)
	new("TextLabel", {
		Name = "Text",
		Parent = pillFrame,
		BackgroundTransparency = 1,
		Position = UDim2.fromOffset(16, 0),
		Size = UDim2.new(1, -40, 1, 0),
		FontFace = Theme.Semi,
		TextSize = 13,
		TextColor3 = C.Text,
		TextXAlignment = Enum.TextXAlignment.Left,
		TextTruncate = Enum.TextTruncate.AtEnd,
		TextTransparency = 1,
		Text = "",
		ZIndex = 52,
	})
	return pillFrame
end

-- signal bars, wifi-like dots and a battery, all from Frames (no images to load)
local function statusIcons(parent: Instance)
	local box = new("Frame", {
		Name = "Icons",
		Parent = parent,
		BackgroundTransparency = 1,
		AnchorPoint = Vector2.new(1, 0.5),
		Position = UDim2.new(1, -24, 0, 25),
		Size = UDim2.fromOffset(62, 12),
		ZIndex = 40,
	})
	for i = 1, 4 do
		local h = 3 + i * 2
		new("Frame", {
			Parent = box,
			AnchorPoint = Vector2.new(0, 1),
			Position = UDim2.new(0, (i - 1) * 4.5, 1, 0),
			Size = UDim2.fromOffset(3, h),
			BackgroundColor3 = C.Text,
			BorderSizePixel = 0,
			ZIndex = 40,
		}, { new("UICorner", { CornerRadius = UDim.new(0, 1) }) })
	end
	-- wifi: three arcs drawn as shrinking rings clipped to their top half
	local wifi = new("Frame", {
		Parent = box,
		BackgroundTransparency = 1,
		ClipsDescendants = true,
		Position = UDim2.fromOffset(21, 0),
		Size = UDim2.fromOffset(16, 11),
		ZIndex = 40,
	})
	for i, s in { 16, 10, 4 } do
		new("Frame", {
			Parent = wifi,
			AnchorPoint = Vector2.new(0.5, 0.5),
			Position = UDim2.fromOffset(8, 11),
			Size = UDim2.fromOffset(s, s),
			BackgroundColor3 = C.Text,
			BackgroundTransparency = if i == 3 then 0 else 1,
			ZIndex = 40,
		}, {
			pill(),
			if i < 3 then new("UIStroke", { Color = C.Text, Thickness = 2 }) else nil :: any,
		})
	end
	local battery = new("Frame", {
		Name = "Battery",
		Parent = box,
		Position = UDim2.fromOffset(40, 0),
		Size = UDim2.fromOffset(20, 11),
		BackgroundTransparency = 1,
		ZIndex = 40,
	}, {
		new("UICorner", { CornerRadius = UDim.new(0, 3) }),
		new("UIStroke", { Color = C.Text, Thickness = 1, Transparency = 0.55 }),
	})
	new("Frame", {
		Name = "Level",
		Parent = battery,
		Position = UDim2.fromOffset(2, 2),
		Size = UDim2.new(0.8, -4, 1, -4),
		BackgroundColor3 = C.Text,
		ZIndex = 41,
	}, { new("UICorner", { CornerRadius = UDim.new(0, 1) }) })
	new("Frame", {
		Parent = battery,
		AnchorPoint = Vector2.new(0, 0.5),
		Position = UDim2.new(1, 1, 0.5, 0),
		Size = UDim2.fromOffset(2, 4),
		BackgroundColor3 = C.Text,
		BackgroundTransparency = 0.5,
		ZIndex = 40,
	})
	return box
end

-- Builds everything under `gui`. Returns the parts init.luau needs.
function Frame.build(gui: ScreenGui)
	local hasArt = Art.Frame ~= nil and Art.Screen ~= nil
	local W = Theme.W
	local H = if hasArt then math.floor(W / Art.Aspect + 0.5) else Theme.H

	-- Holder: what slides up and down; UIScale fits it to the screen
	local holder = new("Frame", {
		Name = "Phone",
		Parent = gui,
		AnchorPoint = Vector2.new(1, 1),
		Size = UDim2.fromOffset(W, H),
		BackgroundTransparency = 1,
		Visible = false,
	})
	local scale = new("UIScale", { Parent = holder })

	local screenRect -- position/size of the screen inside the holder, units
	local body
	if hasArt then
		local s = Art.Screen
		screenRect = { x = s[1] * W, y = s[2] * H, w = s[3] * W, h = s[4] * H }
		body = new("ImageLabel", {
			Name = "Body",
			Parent = holder,
			Size = UDim2.fromScale(1, 1),
			BackgroundTransparency = 1,
			Image = Art.Frame,
			ScaleType = Enum.ScaleType.Stretch,
			ZIndex = 60, -- drawn over the screen: its black glass hides the screen's corners
		})
	else
		local b = Theme.Bezel
		screenRect = { x = b, y = b, w = W - 2 * b, h = H - 2 * b }
		body = new("Frame", {
			Name = "Body",
			Parent = holder,
			Size = UDim2.fromScale(1, 1),
			BackgroundColor3 = C.Glass,
			BorderSizePixel = 0,
			ZIndex = 1,
		}, {
			corner(Theme.BodyRadius),
			-- titanium band around the edge
			new("UIStroke", { Thickness = 3.5, Color = C.Titanium, ApplyStrokeMode = Enum.ApplyStrokeMode.Border }, {
				metal(90),
			}),
		})
		sideButton(holder, "Action", -1, 112, 26)
		sideButton(holder, "VolumeUp", -1, 160, 46)
		sideButton(holder, "VolumeDown", -1, 216, 46)
		sideButton(holder, "Power", 1, 178, 72)
	end

	local screen = new("Frame", {
		Name = "Screen",
		Parent = holder,
		Position = UDim2.fromOffset(screenRect.x, screenRect.y),
		Size = UDim2.fromOffset(screenRect.w, screenRect.h),
		BackgroundColor3 = Color3.new(0, 0, 0),
		BorderSizePixel = 0,
		ClipsDescendants = true,
		ZIndex = 2,
	}, { corner(Theme.ScreenRadius) })

	local wallpaper = new("ImageLabel", {
		Name = "Wallpaper",
		Parent = screen,
		Size = UDim2.fromScale(1, 1),
		BackgroundColor3 = Color3.fromRGB(40, 30, 80),
		BorderSizePixel = 0,
		Image = Art.Wallpaper or "",
		ScaleType = Enum.ScaleType.Crop,
		ZIndex = 2,
	}, { corner(Theme.ScreenRadius) })
	if not Art.Wallpaper then
		new("UIGradient", {
			Parent = wallpaper,
			Rotation = 115,
			Color = ColorSequence.new({
				ColorSequenceKeypoint.new(0, Color3.fromRGB(40, 24, 90)),
				ColorSequenceKeypoint.new(0.55, Color3.fromRGB(150, 60, 140)),
				ColorSequenceKeypoint.new(1, Color3.fromRGB(250, 140, 90)),
			}),
		})
	end

	-- pages live here: the home screen and each app's page (init.luau)
	local pages = new("Frame", {
		Name = "Pages",
		Parent = screen,
		Size = UDim2.fromScale(1, 1),
		BackgroundTransparency = 1,
		ZIndex = 10,
	})

	local status = new("Frame", {
		Name = "StatusBar",
		Parent = screen,
		Size = UDim2.new(1, 0, 0, Theme.StatusBar),
		BackgroundTransparency = 1,
		ZIndex = 40,
	})
	local clock = new("TextLabel", {
		Name = "Time",
		Parent = status,
		BackgroundTransparency = 1,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromOffset(52, 25),
		Size = UDim2.fromOffset(64, 16),
		FontFace = Theme.Semi,
		TextSize = 15,
		TextColor3 = C.Text,
		Text = "9:41",
		ZIndex = 40,
	})
	statusIcons(status)

	local isl = island(screen)
	isl.Position = UDim2.new(0.5, 0, 0, 11)

	local homeBar = new("TextButton", {
		Name = "HomeBar",
		Parent = screen,
		Text = "",
		AutoButtonColor = false,
		AnchorPoint = Vector2.new(0.5, 1),
		Position = UDim2.new(0.5, 0, 1, -7),
		Size = UDim2.fromOffset(104, 5),
		BackgroundColor3 = C.Text,
		BackgroundTransparency = 0.05,
		ZIndex = 45,
	}, { pill() })
	-- bigger invisible hit box so the thin bar is easy to tap
	new("TextButton", {
		Name = "HomeHit",
		Parent = homeBar,
		Text = "",
		BackgroundTransparency = 1,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(0.5, 0.5),
		Size = UDim2.new(1, 40, 0, 22),
		ZIndex = 46,
	})

	-- black cover that fades out when the phone wakes
	local sleepCover = new("Frame", {
		Name = "Sleep",
		Parent = screen,
		Size = UDim2.fromScale(1, 1),
		BackgroundColor3 = Color3.new(0, 0, 0),
		BorderSizePixel = 0,
		ZIndex = 55,
	})

	-- with body art the side buttons are in the picture; give them invisible hit boxes
	local power = holder:FindFirstChild("Power")
	if not power then
		power = new("TextButton", {
			Name = "Power",
			Parent = holder,
			Text = "",
			BackgroundTransparency = 1,
			AnchorPoint = Vector2.new(0, 0),
			Position = UDim2.new(1, -8, 0, H * 0.27),
			Size = UDim2.fromOffset(14, H * 0.13),
			ZIndex = 61,
		})
	end

	return {
		holder = holder,
		scale = scale,
		body = body,
		screen = screen,
		pages = pages,
		status = status,
		clock = clock,
		island = isl,
		homeBar = homeBar,
		sleepCover = sleepCover,
		power = power,
		size = Vector2.new(W, H),
		screenSize = Vector2.new(screenRect.w, screenRect.h),
	}
end

return Frame
