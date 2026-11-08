--!strict
-- Building and road images that fail to load on this client stay grey until the property changes.
-- Roblox often answers the first request for a texture with "Asset content representation is being
-- generated" (it is still making the copy this device needs), and then the part stays untextured.
-- So: every few seconds, preload the images under workspace.City that haven't loaded yet (new
-- parts stream in all the time), and set failed ones again so the client asks once more.
-- Images that loaded are remembered and never checked again.

local ContentProvider = game:GetService("ContentProvider")

local city = workspace:WaitForChild("City", 30)
if not city then
	return
end

local loaded: { [string]: boolean } = {}

local function users(): { [string]: { Instance } }
	local map: { [string]: { Instance } } = {}
	for _, d in city:GetDescendants() do
		local id = if d:IsA("MeshPart") then d.TextureID elseif d:IsA("Texture") or d:IsA("Decal") then d.Texture else ""
		if id ~= "" and not loaded[id] then
			map[id] = map[id] or {}
			table.insert(map[id], d)
		end
	end
	return map
end

local started = os.clock()
while true do
	-- every 3 s for the first two minutes (while the city streams in), then every 15 s
	task.wait(if os.clock() - started < 120 then 3 else 15)
	local map = users()
	local ids = {}
	for id in map do
		table.insert(ids, id)
	end
	if #ids == 0 then
		continue
	end
	local failed = {}
	pcall(ContentProvider.PreloadAsync, ContentProvider, ids, function(id: string, status: Enum.AssetFetchStatus)
		if status == Enum.AssetFetchStatus.Success then
			loaded[id] = true
		else
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
