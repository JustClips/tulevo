--[[
	First-person roll camera: in first person the view tumbles with the body through a roll
	(it turns with the hips and rides along with the head), then settles back on the aim.
	Config.Movement.FirstPersonRollCamera = false turns it off.

	The camera script works out each frame's view from the camera it finds, so the tumble is
	taken off again at the start of every frame (RenderPriority.First) and put back after the
	camera script (RenderPriority.Last). Mouse look keeps working through the roll and the aim
	never drifts. Code that needs where the player is aiming reads RollCamera.view(), which is
	the camera without the tumble.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))

local RollCamera = {}

local FADE = 0.1 -- seconds to blend the tumble in / out

local weight = 0
local tumbled = false
local baseCFrame = CFrame.identity
local baseFocus = CFrame.identity

-- The camera as the camera script left it (no roll tumble). Use this for aiming.
function RollCamera.view(): CFrame
	if tumbled then
		return baseCFrame
	end
	local cam = workspace.CurrentCamera
	return if cam then cam.CFrame else CFrame.identity
end

-- Camera focus without the roll tumble.
function RollCamera.focus(): CFrame
	if tumbled then
		return baseFocus
	end
	local cam = workspace.CurrentCamera
	return if cam then cam.Focus else CFrame.identity
end

local function motor(part: Instance?, name: string): Motor6D?
	local m = part and part:FindFirstChild(name)
	return if m and m:IsA("Motor6D") then m else nil
end

-- How the animation has turned the hips (world rotation) and moved the head (world offset),
-- compared with standing straight.
local function bodyMotion(character: Model): (CFrame?, Vector3?)
	local root = character:FindFirstChild("HumanoidRootPart")
	local lowerTorso = character:FindFirstChild("LowerTorso")
	local upperTorso = character:FindFirstChild("UpperTorso")
	local head = character:FindFirstChild("Head")
	local rootJoint, waist, neck = motor(lowerTorso, "Root"), motor(upperTorso, "Waist"), motor(head, "Neck")
	if not (root and root:IsA("BasePart") and head and head:IsA("BasePart") and rootJoint and waist and neck) then
		return nil, nil
	end
	local hip = root.CFrame * rootJoint.C0
	local turn = (hip * rootJoint.Transform * hip:Inverse()).Rotation
	local headRest = hip * rootJoint.C1:Inverse() * waist.C0 * waist.C1:Inverse() * neck.C0 * neck.C1:Inverse()
	return turn, head.Position - headRest.Position
end

-- isRolling: is the local character mid-roll right now?
function RollCamera.start(isRolling: () -> boolean)
	local player = Players.LocalPlayer

	RunService:BindToRenderStep("RollCameraUndo", Enum.RenderPriority.First.Value, function()
		local cam = workspace.CurrentCamera
		if tumbled and cam and cam.CameraType == Enum.CameraType.Custom then
			cam.CFrame, cam.Focus = baseCFrame, baseFocus
		end
		tumbled = false
	end)

	RunService:BindToRenderStep("RollCamera", Enum.RenderPriority.Last.Value, function(dt)
		local cam = workspace.CurrentCamera
		local character = player.Character
		if not cam or not character or cam.CameraType ~= Enum.CameraType.Custom
			or Config.Movement.FirstPersonRollCamera == false
		then
			weight = 0
			return
		end
		local base, focus = cam.CFrame, cam.Focus
		if (base.Position - focus.Position).Magnitude >= 1 then
			weight = 0 -- not first person
			return
		end
		local want = if isRolling() then 1 else 0
		weight = math.clamp(weight + (if want > weight then dt else -dt) / FADE, 0, 1)
		if weight <= 0 then
			return
		end
		local turn, shift = bodyMotion(character)
		if not turn or not shift then
			return
		end
		if weight < 1 then
			turn = CFrame.identity:Lerp(turn, weight)
			shift *= weight
		end
		local cf = CFrame.new(base.Position + shift) * turn * base.Rotation
		cam.CFrame = cf
		cam.Focus = cf * base:ToObjectSpace(focus)
		baseCFrame, baseFocus, tumbled = base, focus, true
	end)
end

return RollCamera
