-- Home screen: the app grid (4 across) and the dock at the bottom.
-- Apps come from Phone/Apps (see Apps/README in docs/phone.md); Dock = true puts one in the dock.
local TweenService = game:GetService("TweenService")

local Theme = require(script.Parent.Theme)
local Frame = require(script.Parent.Frame)

local new, corner = Frame.new, Frame.corner
local C = Theme.Colors

local Home = {}

local COLS = 4
local CELL_H = 80 -- grid row height (icon + name); cell width = a quarter of the row
local SIDE = 16 -- space between the screen edge and the first / last icon column
local DOCK_H = 78

-- One app icon: rounded square in the app's colour, picture or a letter, name under it.
-- onClick runs when it is pressed. withLabel = false for the dock.
local function icon(app, parent: Instance, withLabel: boolean, onClick)
	local s = Theme.IconSize
	local cell = new("Frame", {
		Name = app.Id,
		Parent = parent,
		BackgroundTransparency = 1,
		LayoutOrder = app.Order or 100,
		ZIndex = 12,
	})
	local button = new("ImageButton", {
		Name = "Icon",
		Parent = cell,
		AutoButtonColor = false,
		AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.new(0.5, 0, 0, if withLabel then 4 else (DOCK_H - s) / 2),
		Size = UDim2.fromOffset(s, s),
		BackgroundColor3 = app.Color or Color3.fromRGB(90, 90, 100),
		BorderSizePixel = 0,
		Image = "",
		ZIndex = 12,
	}, {
		corner(Theme.IconRadius),
		-- soft top-light so flat colours look like app icons
		new("UIGradient", {
			Rotation = 90,
			Color = ColorSequence.new(Color3.new(1, 1, 1), Color3.fromRGB(200, 200, 200)),
		}),
	})
	if app.Icon then
		new("ImageLabel", {
			Parent = button,
			BackgroundTransparency = 1,
			AnchorPoint = Vector2.new(0.5, 0.5),
			Position = UDim2.fromScale(0.5, 0.5),
			Size = UDim2.fromScale(app.IconScale or 0.62, app.IconScale or 0.62),
			Image = app.Icon,
			ZIndex = 13,
		})
	else
		new("TextLabel", {
			Parent = button,
			BackgroundTransparency = 1,
			Size = UDim2.fromScale(1, 1),
			FontFace = Theme.Bold,
			TextSize = 24,
			TextColor3 = C.Text,
			Text = app.Glyph or string.sub(app.Name, 1, 1),
			ZIndex = 13,
		})
	end
	if withLabel then
		new("TextLabel", {
			Name = "Label",
			Parent = cell,
			BackgroundTransparency = 1,
			AnchorPoint = Vector2.new(0.5, 0),
			Position = UDim2.new(0.5, 0, 0, s + 9),
			Size = UDim2.new(1, -2, 0, 14),
			FontFace = Theme.Regular,
			TextSize = 11.5,
			TextColor3 = C.Text,
			TextTruncate = Enum.TextTruncate.AtEnd,
			Text = app.Name,
			TextStrokeColor3 = Color3.new(0, 0, 0),
			TextStrokeTransparency = 0.8,
			ZIndex = 12,
		})
	end
	-- press: the icon dips a little, like iOS
	-- press: the icon sinks a little and darkens, springs back on release (iOS feel)
	local scale = new("UIScale", { Parent = button })
	local dim = new("Frame", {
		Name = "Dim",
		Parent = button,
		Size = UDim2.fromScale(1, 1),
		BackgroundColor3 = Color3.new(0, 0, 0),
		BackgroundTransparency = 1,
		ZIndex = 14,
	}, { corner(Theme.IconRadius) })
	local function press(down: boolean)
		local info = if down
			then TweenInfo.new(0.1, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
			else TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out)
		TweenService:Create(scale, info, { Scale = if down then 0.88 else 1 }):Play()
		TweenService:Create(dim, TweenInfo.new(0.12), { BackgroundTransparency = if down then 0.75 else 1 }):Play()
	end
	button.MouseButton1Down:Connect(function()
		press(true)
	end)
	button.MouseLeave:Connect(function()
		press(false)
	end)
	button.MouseButton1Up:Connect(function()
		press(false)
	end)
	button.Activated:Connect(function()
		press(false)
		onClick(app)
	end)
	return cell, button
end

-- Builds the home page under `pages`. apps = sorted list; onOpen(app) opens one.
function Home.build(pages: Frame, apps, onOpen)
	local page = new("Frame", {
		Name = "Home",
		Parent = pages,
		AnchorPoint = Vector2.new(0.5, 0.5), -- UIScale shrinks/grows it around the middle
		Position = UDim2.fromScale(0.5, 0.5),
		Size = UDim2.fromScale(1, 1),
		BackgroundTransparency = 1,
		ZIndex = 11,
	})
	new("UIScale", { Name = "Zoom", Parent = page }) -- Motion: sinks back while an app is open
	local buttons = {}

	local grid = new("Frame", {
		Name = "Grid",
		Parent = page,
		BackgroundTransparency = 1,
		AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.new(0.5, 0, 0, Theme.StatusBar + 22),
		Size = UDim2.new(1, -2 * SIDE, 1, -(Theme.StatusBar + 22 + DOCK_H + 44)),
		ZIndex = 11,
	}, {
		-- 4 equal columns that always fit the screen width, so spacing stays even
		new("UIGridLayout", {
			CellSize = UDim2.new(1 / COLS, 0, 0, CELL_H),
			CellPadding = UDim2.fromOffset(0, 12),
			FillDirectionMaxCells = COLS,
			HorizontalAlignment = Enum.HorizontalAlignment.Left,
			SortOrder = Enum.SortOrder.LayoutOrder,
		}),
	})

	local dock = new("Frame", {
		Name = "Dock",
		Parent = page,
		AnchorPoint = Vector2.new(0.5, 1),
		Position = UDim2.new(0.5, 0, 1, -26),
		Size = UDim2.new(1, -2 * (SIDE - 6), 0, DOCK_H),
		BackgroundColor3 = C.Dock,
		BackgroundTransparency = 0.45,
		BorderSizePixel = 0,
		ZIndex = 11,
	}, {
		corner(30),
		-- frosted glass: darker tint with a light top edge
		new("UIGradient", {
			Rotation = 90,
			Color = ColorSequence.new(Color3.fromRGB(110, 110, 130), Color3.fromRGB(50, 50, 66)),
		}),
		new("UIStroke", { Color = Color3.new(1, 1, 1), Transparency = 0.82, Thickness = 1 }),
		new("UIPadding", { PaddingLeft = UDim.new(0, 6), PaddingRight = UDim.new(0, 6) }),
		-- same 4 columns as the grid so dock icons line up with the icons above
		new("UIGridLayout", {
			CellSize = UDim2.new(1 / COLS, 0, 1, 0),
			CellPadding = UDim2.fromOffset(0, 0),
			FillDirectionMaxCells = COLS,
			HorizontalAlignment = Enum.HorizontalAlignment.Center,
			SortOrder = Enum.SortOrder.LayoutOrder,
		}),
	})

	for _, app in apps do
		local _, button = icon(app, if app.Dock then dock else grid, not app.Dock, onOpen)
		buttons[app.Id] = button
	end
	return page, buttons
end

return Home
