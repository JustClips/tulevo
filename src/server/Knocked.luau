--[[
	Knocked down instead of dying (Dev 2026-11-06).

	When a player's health hits 0 they don't respawn. They fall over as a ragdoll and lie on
	the floor with the "ВЫ РАНЕНЫ" screen (Client/Knocked.client.luau):
	  - "Ожидать помощи": stay down and wait (sets the character attribute WaitingHelp, for a
	    medic / first-aid system later).
	  - "Потерять сознание": respawn now (KnockedRemotes.GiveUp).

	How it works: the Dead humanoid state is turned off (here and on the owning client), so
	Health 0 no longer kills. The server sees Health 0, sets the character attribute Knocked
	and turns every body joint into a loose BallSocket (the root part is welded to the lower
	torso so the camera follows the body). The client puts the humanoid in the Physics state,
	stops all animations and gives the body a small random push, so everyone lands differently.

	Knocked.attach(player, character, respawn, onRevive) is called by CharacterSetup for every
	new character. Knocked.revive(character, health?) stands a knocked player back up (for
	medics / first-aid kits later). Anything that still really kills (falling into the void)
	respawns as before.
]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local Guard = require(script.Parent:WaitForChild("Guard"))

local Knocked = {}

local remotes = Instance.new("Folder")
remotes.Name = "KnockedRemotes"
local GiveUp = Instance.new("RemoteEvent")
GiveUp.Name = "GiveUp" -- client -> server: "Потерять сознание"
GiveUp.Parent = remotes
local WaitHelp = Instance.new("RemoteEvent")
WaitHelp.Name = "WaitHelp" -- client -> server: "Ожидать помощи"
WaitHelp.Parent = remotes
local ResetRemote = Instance.new("RemoteEvent")
ResetRemote.Name = "Reset" -- client -> server: Roblox menu "Reset Character" knocks you down
ResetRemote.Parent = remotes
remotes.Parent = ReplicatedStorage

type Entry = {
	player: Player,
	respawn: () -> (),
	onRevive: (() -> ())?,
	saved: { [Instance]: any }, -- joints we turned off -> nothing; parts -> their old CanCollide
	added: { Instance },
}

local entries: { [Model]: Entry } = {}

-- how far each joint may bend in the ragdoll (cone angle, twist) in degrees
local LIMITS = {
	Neck = { 35, 30 },
	Waist = { 25, 20 },
	LeftShoulder = { 80, 45 },
	RightShoulder = { 80, 45 },
	LeftElbow = { 70, 10 },
	RightElbow = { 70, 10 },
	LeftWrist = { 30, 15 },
	RightWrist = { 30, 15 },
	LeftHip = { 60, 25 },
	RightHip = { 60, 25 },
	LeftKnee = { 70, 10 },
	RightKnee = { 70, 10 },
	LeftAnkle = { 25, 10 },
	RightAnkle = { 25, 10 },
}
local DEFAULT_LIMIT = { 40, 20 }

local function settings()
	return Config.Knocked or {}
end

-- A joint's two parts and its rest offsets (Motor6D or AnimationConstraint, see Shared/Joints).
local function jointInfo(j: Instance): (BasePart?, BasePart?, CFrame?, CFrame?)
	if j:IsA("Motor6D") then
		return j.Part0, j.Part1, j.C0, j.C1
	end
	if j:IsA("AnimationConstraint") then
		local a0, a1 = j.Attachment0, j.Attachment1
		local p0 = a0 and a0.Parent
		local p1 = a1 and a1.Parent
		if p0 and p0:IsA("BasePart") and p1 and p1:IsA("BasePart") then
			return p0, p1, a0.CFrame, a1.CFrame
		end
	end
	return nil, nil, nil, nil
end

-- A rotation whose X axis (the BallSocket's axis) points along dir.
local function axisAlong(dir: Vector3): CFrame
	local x = if dir.Magnitude > 0.05 then dir.Unit else Vector3.new(0, -1, 0)
	local ref = if math.abs(x.Y) > 0.9 then Vector3.new(0, 0, 1) else Vector3.new(0, 1, 0)
	local y = (ref - x * ref:Dot(x)).Unit
	return CFrame.fromMatrix(Vector3.zero, x, y, x:Cross(y))
end

local function ragdoll(character: Model, e: Entry)
	local root = character:FindFirstChild("HumanoidRootPart") :: BasePart?
	local joints = {}
	for _, d in character:GetDescendants() do
		if (d:IsA("Motor6D") or d:IsA("AnimationConstraint")) and d.Name ~= "Grip" then
			local p0, p1 = jointInfo(d)
			-- only body joints (both parts are the character's own body parts)
			if p0 and p1 and p0.Parent == character and p1.Parent == character then
				table.insert(joints, d)
			end
		end
	end
	for _, j in joints do
		local p0, p1, c0, c1 = jointInfo(j)
		if not (p0 and p1 and c0 and c1) then
			continue
		end
		local isRoot = p0 == root or p1 == root
		if isRoot then
			-- root part stays glued to the lower torso, so the camera follows the body
			local w = Instance.new("Weld")
			w.Name = "KnockedRootWeld"
			w.Part0, w.Part1, w.C0, w.C1 = p0, p1, c0, c1
			w.Parent = p0
			table.insert(e.added, w)
		else
			-- the rest pose of p1 in p0's space, and the joint axis pointing from the joint
			-- toward p1's centre (down the arm/leg, up the neck)
			local rest = c0 * c1:Inverse()
			local joint = CFrame.new(c0.Position) * axisAlong(rest.Position - c0.Position)
			local a0 = Instance.new("Attachment")
			a0.Name = "Knocked" .. j.Name .. "0"
			a0.CFrame = joint
			a0.Parent = p0
			local a1 = Instance.new("Attachment")
			a1.Name = "Knocked" .. j.Name .. "1"
			a1.CFrame = rest:Inverse() * joint
			a1.Parent = p1
			local lim = LIMITS[j.Name] or DEFAULT_LIMIT
			local b = Instance.new("BallSocketConstraint")
			b.Name = "Knocked" .. j.Name
			b.Attachment0, b.Attachment1 = a0, a1
			b.LimitsEnabled = true
			b.UpperAngle = lim[1]
			b.TwistLimitsEnabled = true
			b.TwistLowerAngle, b.TwistUpperAngle = -lim[2], lim[2]
			b.Restitution = 0
			b.Parent = p0
			local nc = Instance.new("NoCollisionConstraint")
			nc.Name = "Knocked" .. j.Name .. "NoCollide"
			nc.Part0, nc.Part1 = p0, p1
			nc.Parent = p0
			table.insert(e.added, a0)
			table.insert(e.added, a1)
			table.insert(e.added, b)
			table.insert(e.added, nc)
		end
		e.saved[j] = true
		;(j :: any).Enabled = false
	end
	-- limbs collide with the floor so the body lies on it instead of sinking in
	for _, part in character:GetChildren() do
		if part:IsA("BasePart") and part ~= root then
			e.saved[part] = part.CanCollide
			part.CanCollide = true
		end
	end
	if root then
		e.saved[root] = root.CanCollide
		root.CanCollide = false
	end
end

local function unragdoll(character: Model, e: Entry)
	for _, inst in e.added do
		inst:Destroy()
	end
	table.clear(e.added)
	for inst, old in e.saved do
		if inst:IsA("BasePart") then
			inst.CanCollide = old
		elseif inst.Parent then
			(inst :: any).Enabled = true
		end
	end
	table.clear(e.saved)
end

-- Other players hold E (or tap/hold on phones) next to the body to pick the player up.
local function addPrompt(character: Model, e: Entry)
	local part = character:FindFirstChild("UpperTorso") or character:FindFirstChild("HumanoidRootPart")
	if not part then
		return
	end
	local cfg = settings()
	local prompt = Instance.new("ProximityPrompt")
	prompt.Name = "KnockedRevive"
	prompt.ActionText = "Поднять"
	prompt.ObjectText = e.player.DisplayName
	prompt.HoldDuration = cfg.ReviveHold or 4
	prompt.MaxActivationDistance = cfg.ReviveDistance or 7
	prompt.RequiresLineOfSight = false
	prompt.KeyboardKeyCode = Enum.KeyCode.E
	prompt.GamepadKeyCode = Enum.KeyCode.ButtonX
	prompt.Parent = part
	table.insert(e.added, prompt)
	-- the server checks what the prompt checks on the helper's screen: standing, close enough
	-- (a little slack for lag), and holding for the whole HoldDuration
	local holdStarted: { [Player]: number } = {}
	local function okHelper(helper: Player): boolean
		local _, _, root = Guard.alive(helper)
		if helper == e.player or not root then
			return false
		end
		return (root.Position - (part :: BasePart).Position).Magnitude <= prompt.MaxActivationDistance + 4
	end
	prompt.PromptButtonHoldBegan:Connect(function(helper)
		if okHelper(helper) then
			holdStarted[helper] = os.clock()
			character:SetAttribute("BeingHelped", helper.DisplayName)
		end
	end)
	prompt.PromptButtonHoldEnded:Connect(function(helper)
		holdStarted[helper] = nil
		character:SetAttribute("BeingHelped", nil)
	end)
	prompt.Triggered:Connect(function(helper)
		character:SetAttribute("BeingHelped", nil)
		local started = holdStarted[helper]
		holdStarted[helper] = nil
		if not okHelper(helper) then
			return
		end
		if not started or os.clock() - started < prompt.HoldDuration * 0.8 then
			Guard.flag(helper, "picked someone up without holding E long enough")
			return
		end
		Knocked.revive(character, cfg.ReviveHealth)
	end)
end

local function knock(character: Model, humanoid: Humanoid)
	local e = entries[character]
	if not e or character:GetAttribute("Knocked") then
		return
	end
	-- out of any seat / car first
	local seat = humanoid.SeatPart
	if seat then
		local weld = seat:FindFirstChild("SeatWeld")
		if weld then
			weld:Destroy()
		end
		humanoid.Sit = false
	end
	-- Roblox's default Health script would heal a knocked player back up from 0
	local health = character:FindFirstChild("Health")
	if health and health:IsA("Script") then
		health.Enabled = false
	end
	character:SetAttribute("WaitingHelp", false)
	character:SetAttribute("KnockedAt", workspace:GetServerTimeNow())
	ragdoll(character, e) -- joints first, so the client already has them when it lets go
	addPrompt(character, e)
	character:SetAttribute("Knocked", true)
end

function Knocked.attach(player: Player, character: Model, respawn: () -> (), onRevive: (() -> ())?)
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	if not humanoid or settings().Enabled == false then
		return
	end
	local e: Entry = { player = player, respawn = respawn, onRevive = onRevive, saved = {}, added = {} }
	entries[character] = e
	humanoid.BreakJointsOnDeath = false
	humanoid.RequiresNeck = false
	humanoid:SetStateEnabled(Enum.HumanoidStateType.Dead, false) -- the client does the same
	character:SetAttribute("Knocked", false)
	humanoid.HealthChanged:Connect(function(hp)
		if hp <= 0 then
			knock(character, humanoid)
		end
	end)
	character.AncestryChanged:Connect(function(_, parent)
		if parent == nil then
			entries[character] = nil
		end
	end)
end

function Knocked.isKnocked(character: Model?): boolean
	return character ~= nil and character:GetAttribute("Knocked") == true
end

-- Stand a knocked player back up with this much health (default Config.Knocked.ReviveHealth).
function Knocked.revive(character: Model, health: number?)
	local e = entries[character]
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	if not e or not humanoid or not Knocked.isKnocked(character) then
		return false
	end
	unragdoll(character, e)
	local script = character:FindFirstChild("Health")
	if script and script:IsA("Script") then
		script.Enabled = true
	end
	humanoid.Health = math.clamp(health or settings().ReviveHealth or 20, 1, humanoid.MaxHealth)
	character:SetAttribute("WaitingHelp", nil)
	character:SetAttribute("BeingHelped", nil)
	character:SetAttribute("KnockedAt", nil)
	character:SetAttribute("Knocked", false) -- the client gets back up
	if e.onRevive then
		task.spawn(e.onRevive)
	end
	return true
end

GiveUp.OnServerEvent:Connect(function(player)
	local character = player.Character
	local e = character and entries[character]
	if not e or not Knocked.isKnocked(character) then
		return
	end
	local at = character:GetAttribute("KnockedAt") or 0
	if workspace:GetServerTimeNow() - at < (settings().GiveUpDelay or 0) then
		return
	end
	entries[character :: Model] = nil
	e.respawn()
end)

ResetRemote.OnServerEvent:Connect(function(player)
	if not Guard.rate(player, "Reset", 0.2, 1) then
		return -- once every 5 s
	end
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if not humanoid or humanoid.Health <= 0 or Knocked.isKnocked(character) or not entries[character :: Model] then
		return
	end
	humanoid.Health = 0 -- HealthChanged -> knock
end)

WaitHelp.OnServerEvent:Connect(function(player)
	if not Guard.rate(player, "WaitHelp", 2, 2) then
		return
	end
	local character = player.Character
	if character and Knocked.isKnocked(character) then
		character:SetAttribute("WaitingHelp", true)
	end
end)

return Knocked
