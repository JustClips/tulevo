--!strict
-- ATMs (art/blender/atm/build_atm.py, docs/atm.md). Every part named Atm<N>Screen in a city
-- model gets:
--   * a glowing display: SurfaceGui "Display" on the screen's outward face (LightInfluence 0),
--     showing the idle "Welcome" screen. A bank UI can draw on / replace this later.
--   * an Attachment "AtmUse" just in front of the screen with a ProximityPrompt "AtmPrompt".
--   * attribute AtmId ("ArkwellAtm_1") and the CollectionService tag "Atm".
-- No banking yet. Using an ATM only announces it:
--   ReplicatedStorage.AtmRemotes.Open (RemoteEvent)   -> FireClient(player, atmId, screenPart)
--   ReplicatedStorage.AtmRemotes.Used (BindableEvent) -> Fire(player, atmId, screenPart) for server code
-- The money itself (Cash / Bank, deposit / withdraw) already lives in Server/Money.luau.

local CollectionService = game:GetService("CollectionService")
local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local USE_DISTANCE = 7
local COOLDOWN = 0.75

local remotes = Instance.new("Folder")
remotes.Name = "AtmRemotes"
local Open = Instance.new("RemoteEvent")
Open.Name = "Open"
Open.Parent = remotes
local Used = Instance.new("BindableEvent")
Used.Name = "Used"
Used.Parent = remotes
remotes.Parent = ReplicatedStorage

local lastUse: { [Player]: number } = {}

-- The screen is a thin box: its display side is the thin axis that points toward the front of
-- the model (the canopy sticks out in front, so the model's box centre is in front of the screen).
local function displayFace(part: BasePart, model: Model): Enum.NormalId
	local size = part.Size
	local axis = if size.X <= size.Y and size.X <= size.Z
		then Enum.NormalId.Right
		elseif size.Y <= size.Z then Enum.NormalId.Top
		else Enum.NormalId.Back
	local toCentre = model:GetBoundingBox().Position - part.Position
	local n = part.CFrame:VectorToWorldSpace(Vector3.FromNormalId(axis))
	if n:Dot(toCentre) >= 0 then
		return axis
	end
	return ({
		[Enum.NormalId.Right] = Enum.NormalId.Left,
		[Enum.NormalId.Top] = Enum.NormalId.Bottom,
		[Enum.NormalId.Back] = Enum.NormalId.Front,
	})[axis] :: Enum.NormalId
end

local function screenImage(model: Model, partName: string): string?
	local raw = model:GetAttribute("LiveSyncTextures")
	if type(raw) ~= "string" then
		return nil
	end
	local ok, map = pcall(HttpService.JSONDecode, HttpService, raw)
	local id = ok and type(map) == "table" and map[partName]
	return if id then `rbxassetid://{id}` else nil
end

local function setupScreen(model: Model, screen: BasePart)
	local n = screen.Name:match("^Atm(%d+)Screen$")
	if not n or screen:GetAttribute("AtmId") then
		return
	end
	local atmId = `{model.Name}_{n}`
	screen:SetAttribute("AtmId", atmId)
	CollectionService:AddTag(screen, "Atm")

	local face = displayFace(screen, model)
	local gui = Instance.new("SurfaceGui")
	gui.Name = "Display"
	gui.Face = face
	gui.LightInfluence = 0
	gui.Brightness = 1.4
	gui.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
	gui.CanvasSize = Vector2.new(800, 600)
	gui.ResetOnSpawn = false
	local img = Instance.new("ImageLabel")
	img.Name = "Idle"
	img.Size = UDim2.fromScale(1, 1)
	img.BackgroundColor3 = Color3.fromRGB(8, 22, 40)
	img.BorderSizePixel = 0
	img.Image = screenImage(model, screen.Name) or ""
	img.Parent = gui
	gui.Parent = screen

	-- soft blue spill on the user's face / the keypad at night
	local glow = Instance.new("SurfaceLight")
	glow.Face = face
	glow.Color = Color3.fromRGB(120, 170, 230)
	glow.Brightness = 0.6
	glow.Range = 6
	glow.Angle = 100
	glow.Shadows = false
	glow.Parent = screen

	local normal = screen.CFrame:VectorToWorldSpace(Vector3.FromNormalId(face))
	local att = Instance.new("Attachment")
	att.Name = "AtmUse"
	att.WorldPosition = screen.Position + normal * 0.8 - Vector3.new(0, 0.6, 0)
	att.Parent = screen

	local prompt = Instance.new("ProximityPrompt")
	prompt.Name = "AtmPrompt"
	prompt.ActionText = "Use ATM"
	prompt.ObjectText = "Arkwell ATM"
	prompt.KeyboardKeyCode = Enum.KeyCode.E
	prompt.HoldDuration = 0.25
	prompt.MaxActivationDistance = USE_DISTANCE
	prompt.RequiresLineOfSight = false
	prompt.Parent = att
	prompt.Triggered:Connect(function(player: Player)
		local now = os.clock()
		if now - (lastUse[player] or 0) < COOLDOWN then
			return
		end
		lastUse[player] = now
		local char = player.Character
		local root = char and char:FindFirstChild("HumanoidRootPart") :: BasePart?
		if not root or (root.Position - att.WorldPosition).Magnitude > USE_DISTANCE + 4 then
			return
		end
		Open:FireClient(player, atmId, screen)
		Used:Fire(player, atmId, screen)
	end)
end

local function setupModel(model: Model)
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") and d.Name:match("^Atm%d+Screen$") then
			setupScreen(model, d)
		end
	end
end

game:GetService("Players").PlayerRemoving:Connect(function(player)
	lastUse[player] = nil
end)

local city = workspace:WaitForChild("City", 30)
local buildings = city and city:WaitForChild("Buildings", 30)
if not buildings then
	return
end
-- Server/CityBuildings loads and styles each model, then sets CityReady.
local function watch(model: Instance)
	if not model:IsA("Model") then
		return
	end
	if model:GetAttribute("CityReady") then
		setupModel(model)
	else
		model:GetAttributeChangedSignal("CityReady"):Once(function()
			setupModel(model)
		end)
	end
end
for _, m in buildings:GetChildren() do
	watch(m)
end
buildings.ChildAdded:Connect(watch)
