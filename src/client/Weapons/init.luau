--[[
	Client weapon controller: picking weapons, aiming, firing, reloading, animations.
	The server (ServerScriptService.Server.Weapons) owns ammo and decides hits; this side
	predicts ammo and plays animations/effects so it feels instant.

	Controls (keyboard / gamepad / phone):
		1-5          pick a wheel slot (Config.Weapons.SlotKeys); same key again or Q holsters
		Left click   fire / attack       (R2, phone Fire button)
		Right click  aim                 (L2, phone Aim button)
		R            reload              (X, phone Reload button)
	TODO later: GTA weapon wheel UI (hold Tab / L1), over-the-shoulder aim camera, crosshair,
	weapon models in hand, sounds.
]]

local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Weapons = require(Shared:WaitForChild("Weapons"))
local State = require(script:WaitForChild("State"))
local AnimSet = require(script:WaitForChild("AnimSet"))
local Effects = require(script:WaitForChild("Effects"))

local Remotes = ReplicatedStorage:WaitForChild("WeaponRemotes")
local player = Players.LocalPlayer

local Controller = {}

local anims = nil
local lastFire = 0
local triggerDown = false
local combo = 0
local ammo: { [string]: { mag: number, reserve: number } } = {}

local SLOT_KEYS = { Enum.KeyCode.One, Enum.KeyCode.Two, Enum.KeyCode.Three, Enum.KeyCode.Four, Enum.KeyCode.Five }

local function character()
	local c = player.Character
	local h = c and c:FindFirstChildOfClass("Humanoid")
	if h and h.Health > 0 then
		return c, h
	end
	return nil, nil
end

local function owned(): { [string]: string } -- slot -> id
	local out = {}
	for id in string.gmatch(player:GetAttribute("Weapons") or "", "[^,]+") do
		local def = Weapons.get(id)
		if def then
			out[def.Class.Slot] = id
		end
	end
	return out
end

local function setTouchButtons(on: boolean)
	-- phone buttons only exist while something is in hand
	for _, name in { "Weapon_Fire", "Weapon_Aim", "Weapon_Reload" } do
		local b = ContextActionService:GetButton(name)
		if b then
			b.Visible = on
		end
	end
end

function Controller.equip(id: string?)
	if id == State.Equipped then
		return
	end
	if anims then
		anims:destroy()
		anims = nil
	end
	State.Equipped = id
	State.Aiming = false
	State.Reloading = false
	Remotes.Equip:FireServer(id)
	local c, h = character()
	if h then
		h.AutoRotate = true
	end
	if id and c and h then
		local def = Weapons.get(id)
		local animator = h:FindFirstChildOfClass("Animator")
		if def and animator then
			anims = AnimSet.new(animator, def.Class)
			anims:play("Hold", 0.2)
			anims:play("Equip")
		end
		local a = ammo[id]
		State.Mag, State.Reserve = a and a.mag or 0, a and a.reserve or 0
	end
	setTouchButtons(id ~= nil)
end

function Controller.reload()
	local id = State.Equipped
	local def = id and Weapons.get(id)
	if not def or def.Class.Kind ~= "Gun" or State.Reloading then
		return
	end
	if State.Mag >= (def.MagSize or 0) or State.Reserve <= 0 then
		return
	end
	State.Reloading = true
	Remotes.Reload:FireServer()
	if anims then
		anims:play("Reload", 0.1, (anims.tracks.Reload and anims.tracks.Reload.Length > 0)
			and anims.tracks.Reload.Length / (def.ReloadTime or 1) or 1)
	end
	task.delay(def.ReloadTime or 1, function()
		if State.Equipped == id then
			State.Reloading = false
		end
	end)
end

-- where the camera is looking (screen centre), as a world point
local function aimPoint(): Vector3
	local cam = workspace.CurrentCamera
	local ray = cam:ViewportPointToRay(cam.ViewportSize.X / 2, cam.ViewportSize.Y / 2)
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = { player.Character :: Instance }
	local hit = workspace:Raycast(ray.Origin, ray.Direction * 1000, params)
	return if hit then hit.Position else ray.Origin + ray.Direction * 1000
end

function Controller.fire()
	local id = State.Equipped
	local def = id and Weapons.get(id)
	local c, h = character()
	if not def or not c or not h or State.Reloading then
		return
	end
	local now = os.clock()
	if now - lastFire < 1 / (def.FireRate or (1 / (def.SwingTime or 0.6))) then
		return
	end
	if def.Class.Kind == "Gun" and State.Mag <= 0 then
		Controller.reload()
		return
	end
	lastFire = now

	local head = c:FindFirstChild("Head") :: BasePart
	local hand = c:FindFirstChild("RightHand") :: BasePart
	local origin = (hand or head).Position
	local target = aimPoint()
	Remotes.Fire:FireServer(origin, target - origin, State.Aiming)

	if def.Class.Kind == "Melee" then
		combo = combo % 3 + 1
		if anims then
			anims:play(`Attack{combo}`)
		end
	else
		State.Mag -= 1
		if anims then
			anims:play("Fire", 0.02)
		end
		Effects.tracer(origin, target) -- the server's hits come back on Shot for others
	end
end

local function bind()
	for i, key in SLOT_KEYS do
		ContextActionService:BindAction(`Weapon_Slot{i}`, function(_, state)
			if state ~= Enum.UserInputState.Begin then
				return Enum.ContextActionResult.Pass
			end
			local slot = Config.Weapons.SlotKeys[i]
			local id = slot and owned()[slot]
			Controller.equip(if id == State.Equipped then nil else id)
			return Enum.ContextActionResult.Sink
		end, false, key)
	end
	ContextActionService:BindAction("Weapon_Holster", function(_, state)
		if state == Enum.UserInputState.Begin then
			Controller.equip(nil)
		end
		return Enum.ContextActionResult.Pass
	end, false, Enum.KeyCode.Q, Enum.KeyCode.DPadDown)

	ContextActionService:BindAction("Weapon_Fire", function(_, state)
		if not State.Equipped then
			return Enum.ContextActionResult.Pass
		end
		triggerDown = state == Enum.UserInputState.Begin
		if triggerDown then
			Controller.fire()
		end
		return Enum.ContextActionResult.Pass
	end, true, Enum.UserInputType.MouseButton1, Enum.KeyCode.ButtonR2)

	ContextActionService:BindAction("Weapon_Aim", function(_, state, obj)
		if not State.Equipped then
			return Enum.ContextActionResult.Pass
		end
		local on
		if obj.UserInputType == Enum.UserInputType.Touch then
			if state ~= Enum.UserInputState.Begin then
				return Enum.ContextActionResult.Pass
			end
			on = not State.Aiming -- phone Aim is a toggle
		else
			on = state == Enum.UserInputState.Begin
		end
		State.Aiming = on
		if anims then
			if on then
				anims:play("Aim", 0.12)
			else
				anims:stop("Aim", 0.15)
			end
		end
		return Enum.ContextActionResult.Pass
	end, true, Enum.UserInputType.MouseButton2, Enum.KeyCode.ButtonL2)

	ContextActionService:BindAction("Weapon_Reload", function(_, state)
		if state == Enum.UserInputState.Begin and State.Equipped then
			Controller.reload()
		end
		return Enum.ContextActionResult.Pass
	end, true, Enum.KeyCode.R, Enum.KeyCode.ButtonX)

	for name, pos in { Weapon_Fire = UDim2.new(1, -95, 1, -210), Weapon_Aim = UDim2.new(1, -170, 1, -210), Weapon_Reload = UDim2.new(1, -95, 1, -270) } do
		ContextActionService:SetTitle(name, name:sub(8))
		ContextActionService:SetPosition(name, pos)
	end
	setTouchButtons(false)
end

function Controller.start()
	bind()

	Remotes.Ammo.OnClientEvent:Connect(function(id, mag, reserve)
		ammo[id] = { mag = mag, reserve = reserve }
		if id == State.Equipped then
			State.Mag, State.Reserve = mag, reserve
		end
	end)

	Remotes.Shot.OnClientEvent:Connect(function(shooter, id, origin, hits)
		local def = Weapons.get(id)
		if shooter == player or not def or def.Class.Kind ~= "Gun" then
			return
		end
		for _, pos in hits do
			Effects.tracer(origin, pos)
		end
		-- TODO(art): play the shooter's fire sound at origin
	end)

	player.CharacterAdded:Connect(function()
		anims = nil
		State.Equipped = nil
		State.Aiming = false
		State.Reloading = false
		setTouchButtons(false)
	end)

	RunService.RenderStepped:Connect(function()
		local id = State.Equipped
		local def = id and Weapons.get(id)
		local c, h = character()
		if not def or not c or not h then
			return
		end
		-- automatic weapons keep firing while the trigger is held
		if triggerDown and def.Automatic then
			Controller.fire()
		end
		-- face where you aim (GTA strafing)
		h.AutoRotate = not State.Aiming
		if State.Aiming then
			local root = c:FindFirstChild("HumanoidRootPart") :: BasePart
			local look = workspace.CurrentCamera.CFrame.LookVector
			local flat = Vector3.new(look.X, 0, look.Z)
			if root and flat.Magnitude > 0.01 then
				root.CFrame = CFrame.lookAt(root.Position, root.Position + flat)
			end
		end
	end)
end

return Controller
