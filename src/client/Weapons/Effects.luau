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

return Effects
