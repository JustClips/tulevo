--[[
	PC mouse look, GTA 5 style (Dev 2026-11-06: "rework sensitivity fully ... copy gta style").

	  * The mouse always turns the camera on PC: on foot, with a gun, in a car. No right-drag,
	    the cursor is hidden and locked to the centre. It comes back by itself while a menu is
	    open (map, inventory, phone, debug panel, knocked screen, chat typing, Roblox menu) and
	    while you hold Left Alt (to click HUD buttons).
	  * Raw 1:1 input: the camera turns by exactly how far the mouse moved this frame, no
	    acceleration, no smoothing. Up/down turns as fast as left/right (Roblox's camera turns
	    up/down 23% slower and only uses the last mouse event of each frame; both are evened out
	    here before the camera script runs).
	  * Separate sensitivities (applied here, not through MouseDeltaSensitivity) like GTA's settings: on foot, aiming, driving. Aiming also scales
	    with the zoom (field of view), so things under the crosshair move across the screen at
	    the same speed zoomed in as zoomed out.

	Numbers live in Config.Camera. MouseLook.set(key, value) changes one for this session (the
	F8 debug panel's Camera page uses it). Roblox's own Esc-menu sensitivity and "invert camera"
	still apply on top.

	Recoil (Weapons/Recoil, after the camera script) and the first-person eye
	(Movement/FirstPersonCamera) are untouched: this only changes how far the mouse turns the
	view, before the camera script runs.
]]

local GuiService = game:GetService("GuiService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local WeaponState = require(
	Players.LocalPlayer:WaitForChild("PlayerScripts"):WaitForChild("Client"):WaitForChild("Weapons"):WaitForChild("State")
)

local MouseLook = {}

local CFG = Config.Camera or {}
local settings = {
	MouseLook = if CFG.MouseLook ~= nil then CFG.MouseLook else true,
	Sensitivity = CFG.Sensitivity or 1,
	AimSensitivity = CFG.AimSensitivity or 1,
	VehicleSensitivity = CFG.VehicleSensitivity or 1,
	AimFovScale = if CFG.AimFovScale ~= nil then CFG.AimFovScale else true,
	EqualAxes = if CFG.EqualAxes ~= nil then CFG.EqualAxes else true,
}
local FREE_KEY = CFG.FreeCursorKey or Enum.KeyCode.LeftAlt
local BASE_FOV = CFG.BaseFieldOfView or 70

-- Roblox CameraModule/CameraInput: radians per (scaled) mouse pixel, x and y
local ROBLOX_SPEED = Vector2.new(1, 0.77) * math.rad(0.5)
local PITCH_LIMIT = math.rad(80)

local changed = Instance.new("BindableEvent")
MouseLook.changed = changed.Event -- (key, value)

function MouseLook.get(key: string): any
	return settings[key]
end

function MouseLook.set(key: string, value: any)
	if settings[key] == nil or settings[key] == value then
		return
	end
	settings[key] = value
	changed:Fire(key, value)
end

-- Other scripts can free the cursor while something is open: MouseLook.free("Shop", true).
local freeReasons: { [string]: boolean } = {}
function MouseLook.free(reason: string, on: boolean)
	freeReasons[reason] = if on then true else nil
end

-- Set by the weapon controller: a gun is out (locks the mouse even with MouseLook off).
MouseLook.gunOut = false

local locked = false
function MouseLook.isLocked(): boolean
	return locked
end

-- The sensitivity used right now (before Roblox's own setting).
function MouseLook.current(): number
	local player = Players.LocalPlayer
	local character = player.Character
	local h = character and character:FindFirstChildOfClass("Humanoid")
	if h and h.SeatPart then
		return settings.VehicleSensitivity
	end
	if WeaponState.Equipped ~= nil and WeaponState.Aiming then
		local s = settings.AimSensitivity
		local cam = workspace.CurrentCamera
		if settings.AimFovScale and cam then
			s *= math.tan(math.rad(cam.FieldOfView / 2)) / math.tan(math.rad(BASE_FOV / 2))
		end
		return s
	end
	return settings.Sensitivity
end

local function visible(pg: Instance, guiName: string, childName: string?): boolean
	local g = pg:FindFirstChild(guiName)
	if not (g and g:IsA("ScreenGui") and g.Enabled) then
		return false
	end
	if not childName then
		return true
	end
	local c = g:FindFirstChild(childName)
	return c ~= nil and c:IsA("GuiObject") and c.Visible
end

local function cursorWanted(player: Player): boolean
	if UserInputService:GetFocusedTextBox() or GuiService.MenuIsOpen or next(freeReasons) then
		return true
	end
	if UserInputService:IsKeyDown(FREE_KEY) then
		return true
	end
	local pg = player:FindFirstChild("PlayerGui")
	if pg then
		if visible(pg, "FullMap") or visible(pg, "Inventory") or visible(pg, "Knocked")
			or visible(pg, "DebugPanel", "Window")
		then
			return true
		end
		local phone = pg:FindFirstChild("Phone")
		local free = phone and phone:FindFirstChild("MouseFree")
		if free and free:IsA("GuiButton") and free.Modal then
			return true
		end
	end
	return false
end

local function shouldLock(player: Player): boolean
	if not UserInputService.MouseEnabled then
		return false
	end
	local last = UserInputService:GetLastInputType()
	if last == Enum.UserInputType.Touch or string.find(last.Name, "Gamepad") then
		return false
	end
	if not (settings.MouseLook or MouseLook.gunOut) then
		return false
	end
	local cam = workspace.CurrentCamera
	if not cam or cam.CameraType ~= Enum.CameraType.Custom then
		return false
	end
	local character = player.Character
	local h = character and character:FindFirstChildOfClass("Humanoid")
	if not h or h.Health <= 0 or character:GetAttribute("Knocked") == true then
		return false
	end
	return not cursorWanted(player)
end

-- mouse movement since the last frame: all of it, and the last event alone (what the Roblox
-- camera script will use)
local sum = Vector2.zero
local last = Vector2.zero

function MouseLook.start()
	local player = Players.LocalPlayer

	UserInputService.InputChanged:Connect(function(input)
		if input.UserInputType == Enum.UserInputType.MouseMovement then
			local d = Vector2.new(input.Delta.X, input.Delta.Y)
			sum += d
			last = d
		end
	end)
	UserInputService.WindowFocusReleased:Connect(function()
		sum, last = Vector2.zero, Vector2.zero
	end)

	UserInputService.MouseDeltaSensitivity = 1 -- sensitivity is applied here instead
	RunService:BindToRenderStep("MouseLook", Enum.RenderPriority.Camera.Value - 1, function()
		local lock = shouldLock(player)
		if lock then
			-- every frame: the camera script can put its own mouse behaviour back
			UserInputService.MouseBehavior = Enum.MouseBehavior.LockCenter
		elseif locked then
			UserInputService.MouseBehavior = Enum.MouseBehavior.Default
		end
		if lock ~= locked then
			UserInputService.MouseIconEnabled = not lock
		end
		locked = lock

		local all, one = sum, last
		sum, last = Vector2.zero, Vector2.zero
		if not lock or (all.X == 0 and all.Y == 0) then
			return
		end
		-- the turn we want: every event this frame, times the sensitivity for the state you're
		-- in, same speed both ways. The camera script adds the last event at its own speeds
		-- right after this, so only the difference is put on here.
		local sens = MouseLook.current()
		local speedY = if settings.EqualAxes then ROBLOX_SPEED.X else ROBLOX_SPEED.Y
		local want = Vector2.new(all.X * ROBLOX_SPEED.X, all.Y * speedY) * sens
		local robloxTurn = Vector2.new(one.X * ROBLOX_SPEED.X, one.Y * ROBLOX_SPEED.Y)
		local extra = want - robloxTurn
		if math.abs(extra.X) < 1e-7 and math.abs(extra.Y) < 1e-7 then
			return
		end
		local ok, invert = pcall(function()
			return UserSettings():GetService("UserGameSettings"):GetCameraYInvertValue()
		end)
		if ok and typeof(invert) == "number" then
			extra = Vector2.new(extra.X, extra.Y * invert)
		end
		local cam = workspace.CurrentCamera
		if not cam then
			return
		end
		local cf = cam.CFrame
		local look = cf.LookVector
		local yaw = math.atan2(-look.X, -look.Z)
		local pitch = math.asin(math.clamp(look.Y, -1, 1))
		pitch = math.clamp(pitch - extra.Y, -PITCH_LIMIT, PITCH_LIMIT)
		yaw -= extra.X
		cam.CFrame = CFrame.new(cf.Position) * CFrame.fromEulerAnglesYXZ(pitch, yaw, 0)
	end)
end

return MouseLook
