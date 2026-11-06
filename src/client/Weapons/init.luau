--[[
	Client weapon controller: picking weapons, aiming, firing, reloading, animations.
	The server (ServerScriptService.Server.Weapons) owns ammo and decides hits; this side
	predicts ammo and plays animations/effects so it feels instant.

	Controls (keyboard / gamepad / phone):
		1-3          the inventory's quick slots (Client/Inventory): a gun there comes out,
		             the same key puts it on your back (D-pad left / up / right, the quick
		             bar at the bottom of the screen); dragging a gun onto / off Active items
		             in the inventory does the same
		Left click   fire / attack       (R2, phone Fire button)
		Right click  aim                 (L2, phone Aim button)
		R            reload              (X, phone Reload button)
	Everyone spawns holding Config.Weapons.EquipOnSpawn (the carbine rifle, in quick slot 1).
	Controller.equip(id) is the one way in and out of the hand (nil = on the back).

	Gun poses (Weapons/AnimSet, clips from art/anim/gun.py) follow what you're doing:
	Hold (low ready) walking/standing, Sprint (low ready, muzzle down), Aim (shouldered; also
	for ~0.3 s after firing from the hip), Tuck in rolls, Air in jumps and falls, Lowered when
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
local Pouches = require(Shared:WaitForChild("Armor"):WaitForChild("Pouches"))
local State = require(script:WaitForChild("State"))
local AnimSet = require(script:WaitForChild("AnimSet"))
local Effects = require(script:WaitForChild("Effects"))
local GunPose = require(script:WaitForChild("GunPose"))
local Movement = require(script.Parent:WaitForChild("Movement"))
local MoveInput = require(script.Parent:WaitForChild("Movement"):WaitForChild("Input"))

local Remotes = ReplicatedStorage:WaitForChild("WeaponRemotes")
local player = Players.LocalPlayer

local Controller = {}

local anims = nil
local holstering = nil -- the previous AnimSet while the holster clip finishes
local lastHeld: string? = nil -- the weapon you last had out (Q takes it out again)
local drawUntil = 0 -- os.clock() until the gun drawn off the back is in hand
local reloadToken = 0 -- bumps on every reload and weapon change, so an old reload's timer is ignored
local equippedAt = 0
local lastResync = 0
local resyncs = 0
local lastClip = "" -- debug: which equip clip played
local function log(...)
	if Config.Weapons.Debug then
		print("[Weapons]", ...)
	end
end
local lastFire = 0
local triggerDown = false
local combo = 0
local ammo: { [string]: { mag: number, reserve: number } } = {}
local hipUntil = 0 -- gun stays up this long after a hip-fire shot
local HIP_RAISE = 0.3 -- long enough to stay up between automatic shots, short enough to drop right after
local wasRaised = false
local zoomed = false
local baseFov: number? = nil
local lastPoseSent = 0
local sentTwist, sentPitch = 0, 0
local sentLean = 0


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

-- Which part the gun model is on right now ("RightHand", "UpperTorso" = on the back); the
-- server sets it (Server/Weapons/GunModel).
local function gunHeldBy(c: Model?): string?
	local gun = c and c:FindFirstChild("Gun")
	local on = gun and gun:GetAttribute("On")
	return if typeof(on) == "string" then on else nil
end

function Controller.equip(id: string?)
	if id == State.Equipped or (id and (State.InVehicle or State.Dressing)) then
		return
	end
	local c0 = player.Character
	if holstering then
		holstering:destroy()
		holstering = nil
	end
	if anims then
		local old = anims
		anims = nil
		local clip = old.tracks.Holster
		if id == nil and clip and gunHeldBy(c0) == "RightHand" then
			-- Q: the rifle goes up over the right shoulder onto the back (the server moves the
			-- weld when the hand gets there, Server/Weapons/GunModel HolsterSwap). Everything
			-- else stops (a reload in progress is cut short, the server puts the mag back).
			for slot in old.tracks do
				if slot ~= "Holster" then
					old:stop(slot, 0.15)
				end
			end
			old:play("Holster", 0.1)
			holstering = old
			task.delay(if clip.Length > 0 then clip.Length else 1.05, function()
				if holstering == old then
					holstering = nil
					old:destroy()
				end
			end)
		else
			old:destroy()
		end
	end
	drawUntil = 0
	reloadToken += 1
	triggerDown = false -- a trigger held through the swap doesn't keep firing the new gun
	if id then
		lastHeld = id
	end
	equippedAt = os.clock()
	resyncs = 0
	log("equip", id, "gun on", gunHeldBy(c0), "server has", player:GetAttribute("Weapon"))
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
			local gun = c:FindFirstChild("Gun")
			if anims:has("Draw") and gun and gun:GetAttribute("WeaponId") == id and gunHeldBy(c) == "UpperTorso" then
				-- off the back: reach over the right shoulder, pull it round to the low ready
				local t = anims:play("Draw", 0.1)
				drawUntil = os.clock() + (if t and t.Length > 0 then t.Length else 0.84)
				lastClip = "Draw"
			else
				anims:play("Equip", 0.1)
				lastClip = "Equip"
			end
		end
		local a = ammo[id]
		State.Mag, State.Reserve = a and a.mag or 0, a and a.reserve or 0
	end
	setTouchButtons(id ~= nil)
end

-- Q / D-pad down / phone Gun button: put the gun away, or take out the one you last had
-- (the default gun if that one's gone).
function Controller.toggle()
	if State.Equipped then
		Controller.equip(nil)
		return
	end
	local have = owned()
	local function isOwned(id: string?): boolean
		if not id then
			return false
		end
		for _, v in have do
			if v == id then
				return true
			end
		end
		return false
	end
	local id = if isOwned(lastHeld) then lastHeld elseif isOwned(Config.Weapons.EquipOnSpawn) then Config.Weapons.EquipOnSpawn else nil
	if not id then
		for _, slot in Config.Weapons.SlotKeys do
			if have[slot] then
				id = have[slot]
				break
			end
		end
	end
	if id then
		Controller.equip(id)
	end
end

function Controller.reload()
	local id = State.Equipped
	local def = id and Weapons.get(id)
	if not def or def.Class.Kind ~= "Gun" or State.Reloading or os.clock() < drawUntil then
		return
	end
	if State.Mag >= (def.MagSize or 0) or State.Reserve <= 0 then
		return
	end
	State.Reloading = true
	reloadToken += 1
	local mine = reloadToken
	-- the clip for where the new mag comes from (next vest pouch, lid shut or open; else the
	-- hip), picked before the server moves on to the next pouch (Shared/Armor/Pouches)
	local slot = if player.Character then Pouches.reloadSlot(player.Character, def.Class) else "Reload"
	Remotes.Reload:FireServer()
	if anims then
		if not anims.tracks[slot] then
			slot = "Reload"
		end
		local track = anims.tracks[slot]
		anims:play(slot, 0.1, if track and track.Length > 0 then track.Length / (def.ReloadTime or 1) else 1)
	end
	task.delay(def.ReloadTime or 1, function()
		if reloadToken == mine then
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
	if Movement.busy() or os.clock() < drawUntil then
		return -- no shooting while rolling, jumping, falling (GTA) or still drawing
	end
	if State.Lowered and def.Class.Kind == "Gun" then
		return -- muzzle pushed down by a wall right in front
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
	Remotes.Pose:FireServer(
		State.Twist,
		math.clamp(math.asin(math.clamp(camLook.Y, -1, 1)), -1.2, 1.2),
		State.Aiming,
		true,
		State.FeetPlant,
		math.round(State.Lean * 20) / 20
	)
	Remotes.Fire:FireServer(target - (head or hand).Position)

	if def.Class.Kind == "Melee" then
		combo = combo % 3 + 1
		if anims then
			anims:play(`Attack{combo}`)
		end
	else
		State.Mag -= 1
		-- GTA: shooting from the hip brings the gun up for a moment. Shots while aiming don't,
		-- so letting go of aim drops the gun straight away.
		if not State.Aiming then
			hipUntil = now + HIP_RAISE
		end
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
	-- taking guns out / putting them away: the inventory's quick slots 1-3 (Client/Inventory)
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
		if not on then
			hipUntil = 0 -- letting go of aim leaves it now, even right after shooting
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

-- What the debug readout (Client/WeaponDebug) shows.
function Controller.debug(): { [string]: any }
	local c = player.Character
	local h = c and c:FindFirstChildOfClass("Humanoid")
	local animator = h and h:FindFirstChildOfClass("Animator")
	local guns = 0
	if c then
		for _, child in c:GetChildren() do
			if child.Name == "Gun" then
				guns += 1
			end
		end
	end
	local tracks = 0
	if anims then
		for _ in anims.tracks do
			tracks += 1
		end
	end
	return {
		equipped = State.Equipped,
		serverHas = player:GetAttribute("Weapon"),
		gunOn = gunHeldBy(c),
		guns = guns,
		anims = if anims then `{tracks} clips` else "none",
		-- 0 = the Hold clip hasn't loaded (bad id / no permission)
		holdLength = if anims and anims.tracks.Hold then anims.tracks.Hold.Length else -1,
		playing = if animator then #animator:GetPlayingAnimationTracks() else -1,
		clip = lastClip,
		drawing = math.max(0, drawUntil - os.clock()),
		holstering = holstering ~= nil,
		dressing = State.Dressing,
		inVehicle = State.InVehicle,
		reloading = State.Reloading,
		lastHeld = lastHeld,
	}
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
		holstering = nil
		drawUntil, hipUntil = 0, 0
		reloadToken += 1
		triggerDown = false
		State.Equipped = nil
		State.Aiming = false
		State.Raised = false
		State.Reloading = false
		State.Twist, State.Pitch, State.GaitReverse, State.StrafeSide, State.AimBlend = 0, 0, false, 0, 0
		State.Lean, State.Lowered = 0, false
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
	-- the camera (no right-drag needed); while aiming a dot shows where shots go and the
	-- camera moves over the right shoulder.
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
	local function menuOpen(): boolean
		local pg = player:FindFirstChild("PlayerGui")
		local map = pg and pg:FindFirstChild("FullMap")
		local inv = pg and pg:FindFirstChild("Inventory") -- Client/Inventory window
		return (map and map:IsA("ScreenGui") and map.Enabled)
			or (inv and inv:IsA("ScreenGui") and inv.Enabled)
			or UserInputService:GetFocusedTextBox() ~= nil
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
		-- the dot only while aiming (right click / L2; Dev 2026-11-06), not while hip-firing or
		-- just carrying the gun
		crossGui.Enabled = gunOut and State.Aiming
		dot.Size = if raised then UDim2.fromOffset(4, 4) else UDim2.fromOffset(6, 6)
		-- over the right shoulder while the gun is up (CameraOffset is in the character's
		-- space, and the character faces the camera then)
		local fp = isFirstPerson(player.Character)
		local want = if raised and gunOut and State.Aiming and not fp then 1.6 else 0
		-- leaning while the body faces the camera: the camera slides out with the head (first
		-- person follows the head by itself)
		if raised and not fp then
			want += State.Lean * 1.1
		end
		shoulder += (want - shoulder) * math.min(1, dt * 10)
		-- first person (eye on the head, aim down the sights) is Movement/FirstPersonCamera
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

	-- Q / E lean (hold), on foot with or without a gun; not while sprinting, rolling, in the
	-- air, driving or dressing. Weapons/GunPose turns State.Lean into the body pose.
	local function updateLean(dt: number, h: Humanoid)
		local active = Movement.active()
		local can = h.Health > 0 and not State.InVehicle and not State.Dressing and h.SeatPart == nil
			and active ~= "Sprint" and active ~= "SprintStop" and active ~= "Pivot" and active ~= "Roll"
			and active ~= "Air" and active ~= "Seated"
		local want = 0
		if can then
			want = (if MoveInput.isDown("LeanRight") then 1 else 0) - (if MoveInput.isDown("LeanLeft") then 1 else 0)
		end
		State.Lean += (want - State.Lean) * math.min(1, dt * 12)
		if math.abs(State.Lean) < 0.002 and want == 0 then
			State.Lean = 0
		end
	end

	local sentUp = false
	local sentPlant = false
	local function sendPose(twist: number, pitch: number)
		local now = os.clock()
		local up = State.AimBlend > 0.5
		local plant = State.FeetPlant
		local lean = math.round(State.Lean * 20) / 20 -- steps of 0.05 so it settles
		local changed = math.abs(twist - sentTwist) > 0.03 or math.abs(pitch - sentPitch) > 0.03 or up ~= sentUp
			or plant ~= sentPlant or lean ~= sentLean
		local settled = (twist == 0 and pitch == 0) and (sentTwist ~= 0 or sentPitch ~= 0)
		if (changed and now - lastPoseSent > 0.1) or (settled and now - lastPoseSent > 0.1) then
			lastPoseSent = now
			sentTwist, sentPitch, sentUp, sentPlant, sentLean = twist, pitch, up, plant, lean
			Remotes.Pose:FireServer(twist, pitch, State.Aiming, up, plant, lean)
		end
	end

	RunService.RenderStepped:Connect(function(dt)
		local id = State.Equipped
		local def = id and Weapons.get(id)
		local c, h = character()
		local root = c and c:FindFirstChild("HumanoidRootPart") :: BasePart?
		if def and c and h and root then
			-- self-repair: equipped but no gun animations (they were never made), or the gun
			-- never reached the hand (the server missed it): make them / ask the server again
			local now = os.clock()
			local animator = h:FindFirstChildOfClass("Animator")
			if not anims and animator and now - equippedAt > 0.5 then
				warn(`[Weapons] {id} equipped without its animations; loading them again`)
				anims = AnimSet.new(animator, def.Class)
				anims:play("Hold", 0.2)
			end
			if def.Model and now - equippedAt > 1.5 and now > drawUntil + 1 and gunHeldBy(c) ~= "RightHand" and now - lastResync > 2 and resyncs < 3 then
				lastResync = now
				resyncs += 1
				warn(`[Weapons] {id} still not in hand (gun on {gunHeldBy(c)}, server has {player:GetAttribute("Weapon")}); asking the server again`)
				Remotes.Equip:FireServer(id)
			end
		end
		if not def or not c or not h or not root then
			State.Raised, State.Twist, State.Pitch, State.GaitReverse = false, 0, 0, false
			State.StrafeSide, State.AimBlend, State.Lowered = 0, 0, false
			if h and root then
				updateLean(dt, h)
			else
				State.Lean = 0
			end
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
		State.Raised = (State.Aiming or now < hipUntil) and def.Class.Kind == "Gun" and now >= drawUntil
		local up = State.Raised and not State.Reloading -- gun at the shoulder
		-- first person: the gun is carried at the shoulder (visible, lower right) and the body
		-- follows the view, like a shooter's viewmodel; sprinting still carries it across
		local fpReady = isFirstPerson(c) and def.Class.Kind == "Gun" and not rolling and not airborne
			and active ~= "Sprint" and not State.Reloading
		local ready = up or fpReady
		updateLean(dt, h)
		-- aiming while standing: feet stay planted and step to turn (Weapons/GunPose)
		State.FeetPlant = ready and not rolling and not airborne and active ~= "Crouch"

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
			State.AimBlend, State.Lowered = 0, false
			return
		end
		-- which pose loop the arms use
		local pose = if rolling
			then "Tuck"
			elseif ready then "Aim"
			elseif airborne then "Air"
			elseif active == "Sprint" or active == "Pivot" then "Sprint"
			elseif active == "Crouch" then "CrouchHold"
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
		-- into and out of Aim quickly (dropping the gun after aiming shouldn't lag)
		local quick = pose == "Aim" or pose == "Tuck" or anims:weight("Aim") > 0.05
		anims:blend({ [pose] = 1 }, dt, if quick then 18 else 10)
		State.Lowered = pose == "Lowered"
		State.AimBlend = if rolling then 0 else anims:weight("Aim")
	end)
end

return Controller
