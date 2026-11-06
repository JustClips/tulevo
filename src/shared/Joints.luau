--[[
	Character joints, whichever kind the rig has.

	R15 joints used to be Motor6Ds. With Roblox's Avatar Joint Upgrade (Workspace
	AvatarJointUpgrade, the default for new games) characters get AnimationConstraints
	instead, with the same names (Root, Waist, Neck, RightHip, ...). Code that only looked for
	Motor6Ds found nothing, so poses never applied. Use this for any joint work:

		local waist = Joints.find(character, "UpperTorso", "Waist")
		Joints.c0(waist), Joints.c1(waist), Joints.setC0(waist, cf), waist.Transform

	Both kinds place the child part the same way:
		Part1 = Part0 * C0 * Transform * C1:Inverse()
	For an AnimationConstraint, C0 / C1 are its Attachment0 / Attachment1 CFrames.
]]

local Joints = {}

local function isJoint(j: Instance?): boolean
	if not j then
		return false
	end
	if j:IsA("Motor6D") then
		return true
	end
	return j:IsA("AnimationConstraint") and (j :: any).Attachment0 ~= nil and (j :: any).Attachment1 ~= nil
end

-- The joint called name, looked for in partName first (where Roblox puts it), then anywhere
-- in the character.
function Joints.find(character: Model, partName: string, name: string): any
	local part = character:FindFirstChild(partName)
	local j = part and part:FindFirstChild(name)
	if isJoint(j) then
		return j
	end
	for _, d in character:GetDescendants() do
		if d.Name == name and isJoint(d) then
			return d
		end
	end
	return nil
end

function Joints.isMotor(j: any): boolean
	return j:IsA("Motor6D")
end

function Joints.c0(j: any): CFrame
	return if j:IsA("Motor6D") then j.C0 else j.Attachment0.CFrame
end

function Joints.c1(j: any): CFrame
	return if j:IsA("Motor6D") then j.C1 else j.Attachment1.CFrame
end

function Joints.setC0(j: any, cf: CFrame)
	if j:IsA("Motor6D") then
		j.C0 = cf
	else
		j.Attachment0.CFrame = cf
	end
end

-- Part0 of the joint (the parent part)
function Joints.part0(j: any): BasePart?
	if j:IsA("Motor6D") then
		return j.Part0
	end
	local a = j.Attachment0
	local p = a and a.Parent
	return if p and p:IsA("BasePart") then p else nil
end

return Joints
