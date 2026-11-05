--[[
	First-person camera. Roblox puts the first-person camera at a fixed height over the root
	part (plus Humanoid.CameraOffset), which ends up inside the chest when the body crouches,
	leans or rolls differently from that guess. This puts it where the eyes really are, every
	frame:

	  * the eye point on the animated Head (crouching, walking bob all follow),
	  * gun up (shouldered pose): the eye is pinned to the gun, so walking, strafing and turning
	    never move the rifle on screen (it sits low right),
	  * aiming down sights (+ right click): on the sight line, just behind the rear sight
	    ("Sight" attachment, along the gun's own axis) so the rear aperture, front post and
	    crosshair line up,
	  * rolls: the view also tumbles with the hips through the roll and settles back on the
	    aim (Config.Movement.FirstPersonRollCamera = false turns the tumble off).

	The camera script works out each frame's view from the camera it finds, so all of this is
	taken off again at the start of every frame (RenderPriority.First) and put back after the
	camera script (RenderPriority.Last): mouse look keeps working and the aim never drifts.
	Code that needs where the player is aiming reads FirstPersonCamera.view(): the real eye
	position with the un-tumbled look direction.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local WeaponState = require(
	Players.LocalPlayer:WaitForChild("PlayerScripts"):WaitForChild("Client"):WaitForChild("Weapons"):WaitForChild("State")
)

local FirstPersonCamera = {}

local FADE = 0.1 -- seconds to blend the roll tumble in / out
local EYE = Vector3.new(0, 0.15, -0.3) -- eye point in Head space (a little forward of the centre)
local SIGHT_BACK = 0.55 -- ADS eye: this far behind the rear sight aperture, on the sight line
local HIP_EYE = Vector3.new(-0.5, 0.26, 0.7) -- gun up, not aiming: eye from the rear sight (view space)
local ADS_TIME = 0.17 -- seconds for the eye to glide onto the sights and back

local weight = 0
local ads = 0 -- 0..1 how far the eye has moved onto the sights
local applied = false
local baseCFrame = CFrame.identity -- the camera as the camera script left it
local baseFocus = CFrame.identity
local viewCFrame = CFrame.identity -- eye position + un-tumbled look

-- Where the player looks from and toward (no roll tumble). Use this for aiming.
function FirstPersonCamera.view(): CFrame
	if applied then
		return viewCFrame
	end
	local cam = workspace.CurrentCamera
	return if cam then cam.CFrame else CFrame.identity
end

-- Camera focus as the camera script set it.
function FirstPersonCamera.focus(): CFrame
	if applied then
		return baseFocus
	end
	local cam = workspace.CurrentCamera
	return if cam then cam.Focus else CFrame.identity
end

local function motor(part: Instance?, name: string): Motor6D?
	local m = part and part:FindFirstChild(name)
	return if m and m:IsA("Motor6D") then m else nil
end

-- How the animation has turned the hips (world rotation), compared with standing straight.
local function hipTurn(character: Model): CFrame?
	local root = character:FindFirstChild("HumanoidRootPart")
	local rootJoint = motor(character:FindFirstChild("LowerTorso"), "Root")
	if not (root and root:IsA("BasePart") and rootJoint) then
		return nil
	end
	local hip = root.CFrame * rootJoint.C0
	return (hip * rootJoint.Transform * hip:Inverse()).Rotation
end

-- Where the eye should be this frame (world), or nil to leave the camera alone. Every point
-- is worked out fresh from this frame's parts (no smoothing on positions, which lagged behind
-- the walking bob and made the gun swim); only the blend weights between them are smoothed.
local function eyePoint(character: Model, base: CFrame, rolling: boolean, dt: number): Vector3?
	local head = character:FindFirstChild("Head")
	if not (head and head:IsA("BasePart")) then
		return nil
	end
	local eye = head.CFrame * EYE
	local gun = character:FindFirstChild("Gun")
	local sight = gun and gun:FindFirstChild("Sight", true)
	local shouldered = if rolling then 0 else math.clamp(WeaponState.AimBlend or 0, 0, 1)
	local wantAds = WeaponState.Equipped ~= nil and WeaponState.Aiming and WeaponState.Raised and not WeaponState.Reloading and not rolling
	ads = math.clamp(ads + (if wantAds then dt else -dt) / ADS_TIME, 0, 1)
	if not (sight and sight:IsA("Attachment")) or shouldered <= 0 then
		return eye
	end
	-- shouldered: pinned to the gun, rifle low right
	local hip = sight.WorldPosition + base.Rotation * HIP_EYE
	-- aiming down sights: on the gun's own sight line
	local onSights = (sight.WorldCFrame * CFrame.new(0, 0, SIGHT_BACK)).Position
	local s = ads * ads * (3 - 2 * ads) -- ease in/out
	return eye:Lerp(hip:Lerp(onSights, s), shouldered)
end

-- isRolling: is the local character mid-roll right now?
function FirstPersonCamera.start(isRolling: () -> boolean)
	local player = Players.LocalPlayer

	RunService:BindToRenderStep("FirstPersonCameraUndo", Enum.RenderPriority.First.Value, function()
		local cam = workspace.CurrentCamera
		if applied and cam and cam.CameraType == Enum.CameraType.Custom then
			cam.CFrame, cam.Focus = baseCFrame, baseFocus
		end
		applied = false
	end)

	RunService:BindToRenderStep("FirstPersonCamera", Enum.RenderPriority.Last.Value, function(dt)
		local cam = workspace.CurrentCamera
		local character = player.Character
		local base, focus = if cam then cam.CFrame else CFrame.identity, if cam then cam.Focus else CFrame.identity
		if not cam or not character or cam.CameraType ~= Enum.CameraType.Custom
			or (base.Position - focus.Position).Magnitude >= 1 -- not first person
		then
			weight, ads = 0, 0
			return
		end
		local rolling = isRolling()
		local eye = eyePoint(character, base, rolling, dt)
		if not eye then
			return
		end
		local pos = eye

		-- roll tumble
		local turn = CFrame.identity
		local tumbleOn = rolling and Config.Movement.FirstPersonRollCamera ~= false
		weight = math.clamp(weight + (if tumbleOn then dt else -dt) / FADE, 0, 1)
		if weight > 0 then
			local t = hipTurn(character)
			if t then
				turn = if weight < 1 then CFrame.identity:Lerp(t, weight) else t
			end
		end

		local cf = CFrame.new(pos) * turn * base.Rotation
		cam.CFrame = cf
		cam.Focus = cf * base:ToObjectSpace(focus)
		baseCFrame, baseFocus, applied = base, focus, true
		viewCFrame = CFrame.new(pos) * base.Rotation
	end)
end

return FirstPersonCamera
