-- Sizes, colours and fonts the phone shares. All sizes are in "phone units": the phone
-- is built 300 x 620 and the whole thing is scaled to the screen with one UIScale.
local Theme = {}

Theme.W = 300 -- whole phone (body), units
Theme.H = 620
Theme.Bezel = 11 -- black glass border around the screen
Theme.BodyRadius = 50
Theme.ScreenRadius = 40

Theme.StatusBar = 46 -- height of the top strip (time, island, icons)
Theme.IconSize = 52
Theme.IconRadius = 13

local FAMILY = "rbxasset://fonts/families/BuilderSans.json"
Theme.Bold = Font.new(FAMILY, Enum.FontWeight.Bold)
Theme.Semi = Font.new(FAMILY, Enum.FontWeight.SemiBold)
Theme.Regular = Font.new(FAMILY, Enum.FontWeight.Medium)

Theme.Colors = {
	Titanium = Color3.fromRGB(58, 56, 54),
	TitaniumLight = Color3.fromRGB(150, 146, 140),
	TitaniumDark = Color3.fromRGB(28, 27, 26),
	Glass = Color3.fromRGB(4, 4, 5),
	Island = Color3.fromRGB(0, 0, 0),
	Text = Color3.fromRGB(255, 255, 255),
	Dim = Color3.fromRGB(190, 192, 198),
	Page = Color3.fromRGB(16, 16, 20),
	Dock = Color3.fromRGB(255, 255, 255),
}

return Theme
