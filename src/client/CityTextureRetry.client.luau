--!strict
-- Building and road images that fail to load on this client (a just-uploaded image still
-- "being generated", a Roblox hiccup) stay grey until the property changes. Check every image
-- under workspace.City every 15 s for the first 5 minutes, then every minute, and set failed
-- ones again. Starts a minute in, so it doesn't slow the first load.

local ContentProvider = game:GetService("ContentProvider")

local city = workspace:WaitForChild("City", 30)
if not city then
	return
end

local function users(): { [string]: { Instance } }
	local map: { [string]: { Instance } } = {}
	for _, d in city:GetDescendants() do
		local id = if d:IsA("MeshPart") then d.TextureID elseif d:IsA("Texture") or d:IsA("Decal") then d.Texture else ""
		if id ~= "" then
			map[id] = map[id] or {}
			table.insert(map[id], d)
		end
	end
	return map
end

-- First check after a minute: earlier, preloading every image round the player only competes
-- with the first meshes and textures streaming in.
local round = 0
while true do
	round += 1
	task.wait(if round == 1 then 60 elseif round <= 16 then 15 else 60)
	local map = users()
	local ids = {}
	for id in map do
		table.insert(ids, id)
	end
	local failed = {}
	pcall(ContentProvider.PreloadAsync, ContentProvider, ids, function(id: string, status: Enum.AssetFetchStatus)
		if status ~= Enum.AssetFetchStatus.Success then
			table.insert(failed, id)
		end
	end)
	for _, id in failed do
		for _, inst in map[id] do
			local prop = if inst:IsA("MeshPart") then "TextureID" else "Texture"
			pcall(function()
				(inst :: any)[prop] = ""
			end)
			task.defer(function()
				pcall(function()
					(inst :: any)[prop] = id
				end)
			end)
		end
	end
end
