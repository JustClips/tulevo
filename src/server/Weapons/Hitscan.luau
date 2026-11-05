--[[
	Server-side shot resolution. The client sends where it shot from and toward; the server
	checks the origin is near the shooter, adds its own spread, raycasts and applies damage.
	Returns the hit positions (one per pellet) for effects.
]]

local Players = game:GetService("Players")

local Hitscan = {}

local MAX_ORIGIN_OFFSET = 8 -- studs between the shooter's head and the claimed muzzle

local function spreadDir(dir: Vector3, degrees: number): Vector3
	if degrees <= 0 then
		return dir
	end
	local cf = CFrame.lookAt(Vector3.zero, dir)
	local r = math.rad(degrees) * math.sqrt(math.random())
	local a = math.random() * 2 * math.pi
	return (cf * CFrame.Angles(math.cos(a) * r, math.sin(a) * r, 0)).LookVector
end

local function damageAt(def, dist: number): number
	local base = def.Damage or 0
	local start, range = def.FalloffStart or 0, def.Range or 300
	if dist <= start then
		return base
	end
	return base * (1 - 0.5 * math.clamp((dist - start) / math.max(1, range - start), 0, 1))
end

function Hitscan.fire(player: Player, def, origin: Vector3, direction: Vector3, aiming: boolean): { Vector3 }
	local character = player.Character
	local head = character and character:FindFirstChild("Head")
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if not head or not humanoid or humanoid.Health <= 0 then
		return {}
	end
	if (origin - head.Position).Magnitude > MAX_ORIGIN_OFFSET or direction.Magnitude < 0.01 then
		return {}
	end
	direction = direction.Unit

	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = { character }

	if def.Class.Kind == "Melee" then
		local result = workspace:Raycast(head.Position, direction * (def.Reach or 5), params)
		if result then
			local model = result.Instance:FindFirstAncestorOfClass("Model")
			local target = model and model:FindFirstChildOfClass("Humanoid")
			if target and target.Health > 0 then
				target:TakeDamage(def.Damage or 0)
			end
			return { result.Position }
		end
		return {}
	end

	local hits = {}
	local range = def.Range or 300
	local spread = if aiming then def.AimSpread or 0 else def.Spread or 0
	for _ = 1, def.Pellets or 1 do
		local dir = spreadDir(direction, spread)
		local result = workspace:Raycast(origin, dir * range, params)
		if result then
			table.insert(hits, result.Position)
			local model = result.Instance:FindFirstAncestorOfClass("Model")
			local target = model and model:FindFirstChildOfClass("Humanoid")
			if target and target.Health > 0 then
				local dmg = damageAt(def, (result.Position - origin).Magnitude)
				if result.Instance.Name == "Head" then
					dmg *= def.HeadshotMultiplier or 1
				end
				-- TODO(teams/police): friendly-fire and wanted-level rules go here.
				local victim = Players:GetPlayerFromCharacter(model)
				if victim ~= player then
					target:TakeDamage(dmg)
				end
			end
		else
			table.insert(hits, origin + dir * range)
		end
	end
	return hits
end

return Hitscan
