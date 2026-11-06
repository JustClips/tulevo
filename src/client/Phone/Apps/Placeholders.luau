-- Placeholder apps so the home screen is not empty. Each one opens an empty page.
-- When a real app is made, give it its own module in this folder (see docs/phone.md)
-- and delete its line here. Pictures come from Phone/AppIcons (ForgeGUI, art/phone).
local AppIcons = require(script.Parent.Parent.AppIcons)

local function app(id, name, color, order, dock)
	return { Id = id, Name = name, Icon = AppIcons[id], Color = color, Order = order, Dock = dock }
end

return {
	app("Calls", "Phone", Color3.fromRGB(52, 199, 89), 1, true),
	app("Messages", "Messages", Color3.fromRGB(48, 176, 80), 2, true),
	app("Browser", "Browser", Color3.fromRGB(10, 132, 255), 3, true),
	app("Camera", "Camera", Color3.fromRGB(80, 80, 88), 4, true),
	app("Contacts", "Contacts", Color3.fromRGB(142, 142, 147), 10),
	app("Maps", "Maps", Color3.fromRGB(46, 160, 220), 11),
	app("Bank", "Bank", Color3.fromRGB(28, 120, 80), 12),
	app("Jobs", "Jobs", Color3.fromRGB(255, 159, 10), 13),
	app("Garage", "Garage", Color3.fromRGB(220, 60, 60), 14),
	app("Taxi", "Taxi", Color3.fromRGB(240, 200, 30), 15),
	app("Notes", "Notes", Color3.fromRGB(255, 204, 0), 16),
	app("Settings", "Settings", Color3.fromRGB(110, 110, 118), 17),
}
