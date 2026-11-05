--[[
	Client weapon controller: picking weapons, aiming, firing, reloading, animations.
	The server (ServerScriptService.Server.Weapons) owns ammo and decides hits; this side
	predicts ammo and plays animations/effects so it feels instant.

	Controls (keyboard / gamepad / phone):
		1-5          pick a wheel slot (Config.Weapons.SlotKeys); same key again or Q holsters
		Left click   fire / attack       (R2, phone Fire button)
		Right click  aim                 (L2, phone Aim button)
		R            reload              (X, phone Reload button)
	Everyone spawns holding Config.Weapons.EquipOnSpawn (the carbine rifle). Q puts it on
	your back, 5 takes it out again.

	Gun poses (Weapons/AnimSet, clips from art/anim/gun.py) follow what you're doing:
	Hold (low ready) walking/standing, Sprint (rifle across the chest), Aim (shouldered; also
	for ~0.6 s after firing from the hip), Tuck in rolls, Air in jumps and falls, Lowered when
	a wall is right in front. While the gun is up your whole body faces the camera: A/D play
	side-steps and S plays the walk in reverse. Weapons/GunPose locks the chest to the aim
	(yaw and pitch) every frame, for every player.
	TODO later: GTA weapon wheel UI (hold Tab / L1), over-the-shoulder aim camera, crosshair,
	sounds.
]]

local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local TweenService = game:GetService("TweenService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Weapons = require(Shared:WaitForChild("Weapons"))
local State = require(script:WaitForChild("State"))
local AnimSet = require(script:WaitForChild("AnimSet"))
local Effects = require(script:WaitForChild("Effects"))
local GunPose = require(script:WaitForChild("GunPose"))
local Movement = require(script.Parent:WaitForChild("Movement"))

local Remotes = ReplicatedStorage:WaitForChild("WeaponRemotes")
local player = Players.LocalPlayer

local Controller = {}

local anims = nil
local lastFire = 0
local triggerDown = false
local combo = 0
local ammo: { [string]: { mag: number, reserve: number } } = {}
local hipUntil = 0 -- gun stays up this long after a hip-fire shot
local HIP_RAISE = 0.6
local wasRaised = false
local zoomed = false
local baseFov: number? = nil
local lastPoseSent = 0
local sentTwist, sentPitch = 0, 0

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
	if id == State.Equipped or (id and State.InVehicle) then
		return
	end
	if anims then
		anims:destroy()
		anims = nil
	end
	State.Equipped = id
	State.Aiming = false
	State.Raised = false
	State.Reloading = false
	hipUntil = 0
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
			anims:play("Equip", 0.1)
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
	-- the view without the first-person roll tumble
	local view = Movement.view()
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = { player.Character :: Instance }
	local hit = workspace:Raycast(view.Position, view.LookVector * 1000, params)
	return if hit then hit.Position else view.Position + view.LookVector * 1000
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
		if def.AutoReload ~= false then
			Controller.reload()
		end
		return
	end
	lastFire = now

	-- GTA: shooting from the hip first turns you to where the camera looks, then fires
	if def.Class.Kind == "Gun" and not State.Raised then
		local root = c:FindFirstChild("HumanoidRootPart") :: BasePart?
		local look = Movement.view().LookVector
		local flat = Vector3.new(look.X, 0, look.Z)
		if root and flat.Magnitude > 0.01 then
			h.AutoRotate = false
			root.CFrame = CFrame.lookAt(root.Position, root.Position + flat)
		end
		State.Raised = true
		hipUntil = now + HIP_RAISE
	end

	local head = c:FindFirstChild("Head") :: BasePart
	local hand = c:FindFirstChild("RightHand") :: BasePart
	local gun = c:FindFirstChild("Gun")
	local muzzle = gun and gun:FindFirstChild("Muzzle", true)
	local origin = if muzzle and muzzle:IsA("Attachment") then muzzle.WorldPosition else (hand or head).Position
	local target = aimPoint()
	-- the server only gets a direction (from the head, like its own origin) and checks it
	-- against where our body aims, so send the latest aim first
	local camLook = Movement.view().LookVector
	Remotes.Pose:FireServer(State.Twist, math.clamp(math.asin(math.clamp(camLook.Y, -1, 1)), -1.2, 1.2), State.Aiming, true)
	Remotes.Fire:FireServer(target - (head or hand).Position)

	if def.Class.Kind == "Melee" then
		combo = combo % 3 + 1
		if anims then
			anims:play(`Attack{combo}`)
		end
	else
		State.Mag -= 1
		hipUntil = now + HIP_RAISE -- GTA: shooting from the hip brings the gun up
		if anims and anims:weight("Aim") > 0.5 then
			anims:play("Fire", 0.02)
		end
		if muzzle and muzzle:IsA("Attachment") then
			Effects.flash(muzzle)
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
		State.Aiming = on -- the pose itself is blended in the frame loop
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
		local gun = shooter.Character and shooter.Character:FindFirstChild("Gun")
		local muzzle = gun and gun:FindFirstChild("Muzzle", true)
		if muzzle and muzzle:IsA("Attachment") then
			origin = muzzle.WorldPosition
			Effects.flash(muzzle)
		end
		for _, pos in hits do
			Effects.tracer(origin, pos)
		end
		-- TODO(art): play the shooter's fire sound at origin
	end)

	-- spawn holding the default gun (once the server has given it to us)
	local function equipOnSpawn(c: Model)
		local want = Config.Weapons.EquipOnSpawn
		if not want then
			return
		end
		local h = c:WaitForChild("Humanoid", 10) :: Humanoid?
		if not h or not h:WaitForChild("Animator", 10) then
			return
		end
		local deadline = os.clock() + 15
		while os.clock() < deadline and player.Character == c do
			local def = Weapons.get(want)
			if def and owned()[def.Class.Slot] == want then
				break
			end
			player:GetAttributeChangedSignal("Weapons"):Wait()
		end
		task.wait(0.2) -- let the server's CharacterAdded put the gun on the back first
		if player.Character == c and not State.Equipped and not State.InVehicle then
			Controller.equip(want)
		end
	end

	local function onCharacter(c: Model)
		anims = nil
		State.Equipped = nil
		State.Aiming = false
		State.Raised = false
		State.Reloading = false
		State.Twist, State.Pitch, State.GaitReverse, State.StrafeSide, State.AimBlend = 0, 0, false, 0, 0
		wasRaised = false
		setTouchButtons(false)
		task.spawn(equipOnSpawn, c)
	end
	player.CharacterAdded:Connect(onCharacter)
	if player.Character then
		task.spawn(onCharacter, player.Character)
	end

	GunPose.start()

	-- arms follow the jump: dip with the knees, spring on take-off, bounce on landing
	Movement.on(function(event: string, a: any, b: any)
		if not anims or State.Raised then
			return
		end
		if event == "Prep" then
			local t = anims.tracks.JumpPrep
			if t and t.Length > 0 then
				anims:play("JumpPrep", 0.04, t.Length / math.max(0.05, b or 0.12))
			end
		elseif event == "TakeOff" then
			anims:stop("JumpPrep", 0.06)
			anims:play("JumpUp", 0.05)
		elseif event == "Land" then
			anims:stop("JumpUp", 0.08)
			anims:play("Land", 0.05, if a then 1.3 else 1)
		end
	end)

	local wallParams = RaycastParams.new()
	wallParams.FilterType = Enum.RaycastFilterType.Exclude
	wallParams.IgnoreWater = true

	local function setZoom(on: boolean)
		local cam = workspace.CurrentCamera
		if on == zoomed or not cam then
			return
		end
		zoomed = on
		if on then
			baseFov = cam.FieldOfView
		end
		local fov = if on then Config.Weapons.AimFieldOfView or 55 else baseFov or 70
		TweenService:Create(cam, TweenInfo.new(0.2, Enum.EasingStyle.Quad), { FieldOfView = fov }):Play()
	end

	-- GTA camera on PC: while a gun is out the mouse is locked to the screen centre and turns
	-- the camera (no right-drag needed); a dot shows where shots go. Aiming moves the camera
	-- over the right shoulder.
	local crossGui = Instance.new("ScreenGui")
	crossGui.Name = "Crosshair"
	crossGui.IgnoreGuiInset = true
	crossGui.ResetOnSpawn = false
	crossGui.Enabled = false
	local dot = Instance.new("Frame")
	dot.AnchorPoint = Vector2.new(0.5, 0.5)
	dot.Position = UDim2.fromScale(0.5, 0.5)
	dot.Size = UDim2.fromOffset(4, 4)
	dot.BackgroundColor3 = Color3.new(1, 1, 1)
	dot.BorderSizePixel = 0
	local stroke = Instance.new("UIStroke")
	stroke.Color = Color3.new(0, 0, 0)
	stroke.Transparency = 0.4
	stroke.Parent = dot
	dot.Parent = crossGui
	crossGui.Parent = player:WaitForChild("PlayerGui")

	local function isFirstPerson(c: Model?): boolean
		local head = c and c:FindFirstChild("Head") :: BasePart?
		local cam = workspace.CurrentCamera
		-- zoomed all the way in: the camera sits on its focus point
		return head ~= nil and cam ~= nil and (cam.CFrame.Position - cam.Focus.Position).Magnitude < 1
	end

	local mouseLocked = false
	local shoulder = 0
	local adsBase: Vector3? = nil -- CameraOffset before aiming down sights
	local adsOffset = Vector3.zero
	local function menuOpen(): boolean
		local pg = player:FindFirstChild("PlayerGui")
		local map = pg and pg:FindFirstChild("FullMap")
		return (map and map:IsA("ScreenGui") and map.Enabled) or UserInputService:GetFocusedTextBox() ~= nil
	end
	local function updateCamera(dt: number, gunOut: boolean, raised: boolean, h: Humanoid?)
		local lock = gunOut and UserInputService.MouseEnabled and not menuOpen()
		if lock then
			UserInputService.MouseBehavior = Enum.MouseBehavior.LockCenter
		elseif mouseLocked then
			UserInputService.MouseBehavior = Enum.MouseBehavior.Default
		end
		if lock ~= mouseLocked then
			UserInputService.MouseIconEnabled = not lock
		end
		mouseLocked = lock
		crossGui.Enabled = gunOut and (lock or raised)
		dot.Size = if raised then UDim2.fromOffset(4, 4) else UDim2.fromOffset(6, 6)
		-- over the right shoulder while the gun is up (CameraOffset is in the character's
		-- space, and the character faces the camera then)
		local fp = isFirstPerson(player.Character)
		local want = if raised and gunOut and State.Aiming and not fp then 1.6 else 0
		shoulder += (want - shoulder) * math.min(1, dt * 10)
		-- first person + aiming: the eye goes right behind the rear sight (aim down sights)
		local ads = fp and gunOut and State.Aiming and raised and not State.Reloading and Movement.active() ~= "Roll"
		local c = player.Character
		local gun = c and c:FindFirstChild("Gun")
		local sight = gun and gun:FindFirstChild("Sight", true)
		local root = c and c:FindFirstChild("HumanoidRootPart") :: BasePart?
		local cam = workspace.CurrentCamera
		if h and ads and sight and sight:IsA("Attachment") and root and cam then
			if not adsBase then
				adsBase = h.CameraOffset
				adsOffset = h.CameraOffset
			end
			local base = Movement.viewFocus().Position - root.CFrame:VectorToWorldSpace(h.CameraOffset)
			local view = Movement.view()
			local eye = sight.WorldPosition - view.LookVector * 0.55 + view.UpVector * 0.04
			local want3 = root.CFrame:VectorToObjectSpace(eye - base)
			adsOffset = adsOffset:Lerp(want3, math.min(1, dt * 14))
			h.CameraOffset = adsOffset
			return
		elseif h and adsBase then
			adsOffset = adsOffset:Lerp(adsBase, math.min(1, dt * 14))
			h.CameraOffset = adsOffset
			if (adsOffset - adsBase).Magnitude < 0.02 then
				h.CameraOffset = adsBase
				adsBase = nil
			end
			return
		end
		if h then
			local off = h.CameraOffset
			if math.abs(off.X - shoulder) > 0.005 then
				h.CameraOffset = Vector3.new(shoulder, off.Y, off.Z)
			end
		end
	end

	-- First person: Roblox hides your whole character when the camera is in your head. Keep
	-- the arms and the gun visible (runs right after the camera script each frame).
	local SHOW_FIRST_PERSON = {
		RightUpperArm = true, RightLowerArm = true, RightHand = true,
		LeftUpperArm = true, LeftLowerArm = true, LeftHand = true,
	}
	RunService:BindToRenderStep("GunFirstPerson", Enum.RenderPriority.Camera.Value + 1, function()
		local c = player.Character
		if not c or not State.Equipped or not isFirstPerson(c) then
			return
		end
		for _, part in c:GetChildren() do
			if part:IsA("BasePart") and SHOW_FIRST_PERSON[part.Name] then
				part.LocalTransparencyModifier = 0
			end
		end
		local gun = c:FindFirstChild("Gun")
		if gun then
			for _, d in gun:GetDescendants() do
				if d:IsA("BasePart") then
					d.LocalTransparencyModifier = 0
				end
			end
		end
	end)

	local sentUp = false
	local function sendPose(twist: number, pitch: number)
		local now = os.clock()
		local up = State.AimBlend > 0.5
		local changed = math.abs(twist - sentTwist) > 0.03 or math.abs(pitch - sentPitch) > 0.03 or up ~= sentUp
		local settled = (twist == 0 and pitch == 0) and (sentTwist ~= 0 or sentPitch ~= 0)
		if (changed and now - lastPoseSent > 0.1) or (settled and now - lastPoseSent > 0.1) then
			lastPoseSent = now
			sentTwist, sentPitch, sentUp = twist, pitch, up
			Remotes.Pose:FireServer(twist, pitch, State.Aiming, up)
		end
	end

	RunService.RenderStepped:Connect(function(dt)
		local id = State.Equipped
		local def = id and Weapons.get(id)
		local c, h = character()
		local root = c and c:FindFirstChild("HumanoidRootPart") :: BasePart?
		if not def or not c or not h or not root then
			State.Raised, State.Twist, State.Pitch, State.GaitReverse = false, 0, 0, false
			State.StrafeSide, State.AimBlend = 0, 0
			setZoom(false)
			updateCamera(dt, false, false, h)
			if wasRaised and h then
				h.AutoRotate = true
			end
			wasRaised = false
			sendPose(0, 0)
			return
		end
		-- automatic weapons keep firing while the trigger is held
		if triggerDown and def.Automatic then
			Controller.fire()
		end

		local now = os.clock()
		local active = Movement.active()
		local rolling = active == "Roll"
		local airborne = active == "Air"
		State.Raised = (State.Aiming or now < hipUntil) and def.Class.Kind == "Gun"
		local up = State.Raised and not State.Reloading -- gun at the shoulder
		-- first person: the gun is carried at the shoulder (visible, lower right) and the body
		-- follows the view, like a shooter's viewmodel; sprinting still carries it across
		local fpReady = isFirstPerson(c) and def.Class.Kind == "Gun" and not rolling and not airborne
			and active ~= "Sprint" and not State.Reloading
		local ready = up or fpReady

		-- face where you aim (GTA): the whole body locks to the camera direction (bladed into
		-- the rifle stance by Weapons/GunPose); moving sideways plays side-steps and moving
		-- back plays the walk in reverse (Movement/Gait)
		local look = Movement.view().LookVector
		local flat = Vector3.new(look.X, 0, look.Z)
		local side, reverse = 0, false
		if (State.Raised or fpReady) and flat.Magnitude > 0.01 then
			local aimYaw = math.atan2(-flat.X, -flat.Z)
			h.AutoRotate = false
			root.CFrame = CFrame.new(root.Position) * CFrame.Angles(0, aimYaw, 0)
			root.AssemblyAngularVelocity = Vector3.zero
			local move = h.MoveDirection
			if move.Magnitude > 0.1 and not airborne and not rolling then
				-- relative to the hips, which GunPose turns into the rifle stance
				local rel = CFrame.Angles(0, aimYaw - State.HipTurn, 0):VectorToObjectSpace(move)
				local total = math.abs(rel.X) + math.abs(rel.Z)
				side = if total > 0 then rel.X / total else 0
				reverse = rel.Z > 0.1
			end
		elseif wasRaised and not rolling then
			h.AutoRotate = true
		end
		wasRaised = State.Raised or fpReady
		State.GaitReverse = reverse
		State.StrafeSide = side
		State.Twist = 0
		State.Pitch = if ready and not rolling then math.clamp(math.asin(math.clamp(look.Y, -1, 1)), -1.2, 1.2) else 0
		sendPose(State.Twist, State.Pitch)
		setZoom(State.Aiming and up)
		updateCamera(dt, def.Class.Kind == "Gun", State.Raised, h)

		if not anims then
			State.AimBlend = 0
			return
		end
		-- which pose loop the arms use
		local pose = if rolling
			then "Tuck"
			elseif ready then "Aim"
			elseif airborne then "Air"
			elseif active == "Sprint" then "Sprint"
			else "Hold"
		if pose ~= "Tuck" and pose ~= "Air" and anims:has("Lowered") then
			-- muzzle down when a wall is right in front (the gun would go through it)
			wallParams.FilterDescendantsInstances = { c }
			local ut = c:FindFirstChild("UpperTorso") :: BasePart?
			local dir = if up and flat.Magnitude > 0.01 then flat.Unit else Vector3.new(root.CFrame.LookVector.X, 0, root.CFrame.LookVector.Z).Unit
			local reach = Config.Weapons.LowerNearWalls or 2.4
			local hit = ut and workspace:Raycast(ut.Position + Vector3.new(0, 0.3, 0), dir * reach, wallParams)
			if hit and hit.Instance.CanCollide and hit.Instance.Transparency < 1 then
				pose = "Lowered"
			end
		end
		anims:blend({ [pose] = 1 }, dt, if pose == "Aim" or pose == "Tuck" then 16 else 10)
		State.AimBlend = if rolling then 0 else anims:weight("Aim")
	end)
end

return Controller
