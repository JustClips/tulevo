-- Shot effects (client only). Placeholder tracer for now; muzzle flash, sounds, impacts and
-- shell casings go here once the art exists.
local Debris = game:GetService("Debris")

local Effects = {}

function Effects.tracer(from: Vector3, to: Vector3)
	local length = (to - from).Magnitude
	if length < 0.5 then
		return
	end
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.Material = Enum.Material.Neon
	p.Color = Color3.fromRGB(255, 220, 150)
	p.Transparency = 0.3
	p.Size = Vector3.new(0.06, 0.06, length)
	p.CFrame = CFrame.lookAt(from, to) * CFrame.new(0, 0, -length / 2)
	p.Parent = workspace
	Debris:AddItem(p, 0.05)
end

-- Short muzzle flash at the gun's Muzzle attachment.
function Effects.flash(muzzle: Attachment)
	local light = Instance.new("PointLight")
	light.Color = Color3.fromRGB(255, 200, 120)
	light.Range = 10
	light.Brightness = 4
	light.Parent = muzzle
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.Material = Enum.Material.Neon
	p.Color = Color3.fromRGB(255, 210, 130)
	p.Shape = Enum.PartType.Ball
	p.Size = Vector3.new(0.35, 0.35, 0.35) * (0.8 + math.random() * 0.4)
	p.CFrame = muzzle.WorldCFrame * CFrame.new(0, 0, -0.15)
	p.Parent = workspace
	Debris:AddItem(light, 0.05)
	Debris:AddItem(p, 0.04)
end

return Effects
