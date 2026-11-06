--[[
	Puts a weapon's 3D model on the character (server side, so everyone sees it).

		GunModel.hold(character, def)    -- welded in the right hand (the animations aim it)
		GunModel.sling(character, def)   -- on the back (holstered)
		GunModel.remove(character)
		GunModel.inHand(character) / GunModel.onBack(character, id)
		GunModel.cancelReload(character) -- the magazine goes straight back in

	The gun model's "On" attribute names the part it's welded to ("RightHand", "UpperTorso" =
	on the back), so the client and Server/Armor can check it without looking at the welds
	(the magazine's own weld moves to the left hand during a reload).

	The model is loaded by id from Shared.ModelIds[def.Model] and scaled by
	Config.Weapons.GunScale. Its origin is the pistol-grip hold point, muzzle toward -Z.
	HAND_TO_GUN must match art/anim/gun.py (it prints the numbers): the animations are solved
	for exactly this hand offset, so the left hand lands on the handguard.
	"Muzzle" (flash hider, tracers/effects) and "Sight" (rear sight, first-person aiming)
	attachments are added.
]]

local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local ModelIds = require(Shared:WaitForChild("ModelIds"))
local Pouches = require(Shared:WaitForChild("Armor"):WaitForChild("Pouches"))
local SoundIds = require(Shared:WaitForChild("SoundIds"))

local GunModel = {}

-- RightHand -> gun origin (from art/anim/gun.py)
local HAND_TO_GUN = CFrame.new(0, -0.158, 0, 1, 0, 0, 0, 0.3746, 0.9272, 0, -0.9272, 0.3746)
-- Muzzle at scale 1 (studs, gun space), from the imported model
local MUZZLE = Vector3.new(0, 0.269, -1.634)
-- rear sight aperture (first-person aiming puts the camera behind it)
local SIGHT = Vector3.new(0, 0.494, -0.030)
-- On the back (art/anim/gun.py SLUNG): flat on the vest's back plate, muzzle down toward the
-- left hip, stock up behind the right shoulder, pistol grip high on the right shoulder blade
-- (the right hand reaches it over the shoulder).
local BACK = CFrame.fromMatrix(
	Vector3.new(0.45, 0.6, 0.95),
	Vector3.new(0, 0, 1),
	Vector3.new(0.9063, -0.4226, 0),
	Vector3.new(0.4226, 0.9063, 0)
)

-- Reload: the parts move on the beats of Weapon_Rifle_Reload / ReloadPouch<k>[Open]
-- (art/anim/gun.py RELOAD, MAG_IN_HAND, MAG_DRAW_IN_HAND, PARTIAL; seconds at playback speed 1).
-- Old mag: palmed from below (MAG_IN_HAND). New mag: held by its top half (MAG_DRAW_IN_HAND).
local MAG_IN_HAND = CFrame.new(0.4881, 0.0454, 0.1066, 0.4226, 0.9063, 0, -0.8517, 0.3971, -0.342, -0.31, 0.1445, 0.9397)
local MAG_DRAW_IN_HAND =
	CFrame.new(-0.1542, -0.2099, -0.0677, 0.4226, 0.9063, 0, -0.8517, 0.3971, -0.342, -0.31, 0.1445, 0.9397)
local RELOAD_BEATS = {
	grab = 0.4, -- old mag into the left hand
	drop = 0.7, -- old mag falls away
	flap = 0.9, -- pouch lid flips open (FLAP_TIME)
	take = 1.1, -- hand on the mag in the pouch
	swap = 1.2, -- pulled 0.33 up: the full mag takes over from the pouch piece
	partial = 1.58, -- pushed into the well, PARTIAL short; the hand lets go
	seated = 1.74, -- slapped home
	length = 2.45,
}
GunModel.ReloadLength = RELOAD_BEATS.length
local PARTIAL = 0.2
-- Vest pouches (Shared/Armor/Pouches, art/models/ArmorVest/meta.json): the lid turns this far
-- about the back-top edge of its box (110 cuts into the vest, 90 stands stiff).
local FLAP_OPEN = math.rad(100)
local FLAP_TIME = 0.1
-- the magazine top in gun space at scale 1 (art/anim/gun.py MagWell), and how a mag stands in
-- a pouch: the gun's muzzle direction points to the wearer's right
local MAGWELL = Vector3.new(0, 0.211, -0.475)
local POUCH_ROT = CFrame.Angles(0, math.rad(-90), 0)

-- Holster / draw (Weapon_Rifle_Holster / Draw, art/anim/gun.py HOLSTER and draw_beats(),
-- seconds): when the hand has the rifle on the back, the weld moves to the back (holster) or
-- to the hand (draw). The hand waits there ~0.2 s, so a little network lag doesn't show.
GunModel.HolsterSwap = 0.58
GunModel.DrawSwap = 0.256
GunModel.DrawLength = 0.84

local templates: { [string]: Model | false } = {}
local restoreMag: { [BasePart]: () -> () } = {} -- magazine -> put it back in the gun (mid-reload)

local loading: { [string]: boolean } = {}
-- per character: bumps on every attach / remove, so an attach still waiting for its model to
-- load never puts a second gun on a character that has moved on
local attachSeq: { [Model]: number } = setmetatable({}, { __mode = "k" }) :: any

local function load(name: string): Model?
	local id = ModelIds[name]
	if not id then
		return nil
	end
	local ok, container = pcall(InsertService.LoadAsset, InsertService, id)
	if not ok then
		warn(`[GunModel] could not load {name} ({id}): {container}`)
		return nil
	end
	local model = Instance.new("Model")
	model.Name = "Gun"
	local pivot = CFrame.new()
	for _, child in container:GetChildren() do
		if child:IsA("Model") then
			pivot = child:GetPivot()
		end
		child.Parent = model
	end
	container:Destroy()
	model.WorldPivot = pivot
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.Anchored = false
			d.CanCollide = false
			d.CanQuery = false
			d.CanTouch = false
			d.Massless = true
			d.CastShadow = true
		elseif d:IsA("Script") or d:IsA("LocalScript") or d:IsA("JointInstance") or d:IsA("WeldConstraint") then
			d:Destroy()
		end
	end
	local scale = Config.Weapons.GunScale or 1
	if scale ~= 1 then
		model:ScaleTo(scale)
	end
	-- muzzle attachment on the biggest part (the body)
	local body: BasePart? = nil
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") and (not body or d.Size.Magnitude > body.Size.Magnitude) then
			body = d
		end
	end
	if body then
		local a = Instance.new("Attachment")
		a.Name = "Muzzle"
		a.CFrame = body.CFrame:ToObjectSpace(model:GetPivot() * CFrame.new(MUZZLE * scale))
		a.Parent = body
		local sight = Instance.new("Attachment")
		sight.Name = "Sight"
		sight.CFrame = body.CFrame:ToObjectSpace(model:GetPivot() * CFrame.new(SIGHT * scale))
		sight.Parent = body
	end
	return model
end

-- The model, loaded once. LoadAsset yields, so a second caller meanwhile waits for the first
-- one's load (two loads at spawn used to leave two rifles on the character).
local function template(name: string): Model?
	while loading[name] do
		task.wait()
	end
	if templates[name] == nil then
		loading[name] = true
		local ok, model = pcall(load, name)
		if not ok then
			warn(`[GunModel] {name}: {model}`)
		end
		templates[name] = if ok and model then model else false
		loading[name] = nil
	end
	return templates[name] or nil
end

-- Load a model ahead of time (server start), so the first equip doesn't wait for it.
function GunModel.preload(name: string)
	template(name)
end

local function heldOn(character: Model): string?
	local gun = character:FindFirstChild("Gun")
	return gun and gun:GetAttribute("On") or nil
end

function GunModel.inHand(character: Model): boolean
	return heldOn(character) == "RightHand"
end

-- Is this weapon's model slung on the back right now?
function GunModel.onBack(character: Model, id: string): boolean
	local gun = character:FindFirstChild("Gun")
	return gun ~= nil and gun:GetAttribute("WeaponId") == id and heldOn(character) == "UpperTorso"
end

function GunModel.remove(character: Model)
	attachSeq[character] = (attachSeq[character] or 0) + 1
	for _, child in character:GetChildren() do
		if child.Name == "Gun" then
			child:Destroy()
		end
	end
end

local function attach(character: Model, def, partName: string, offset: CFrame)
	local seq = (attachSeq[character] or 0) + 1
	attachSeq[character] = seq
	local t = def and def.Model and template(def.Model) -- yields the first time
	if attachSeq[character] ~= seq then
		return -- a newer attach / remove happened while the model loaded
	end
	if not t and Config.Weapons.Debug then
		warn(`[GunModel] no model for {def and def.Id} (load failed?)`)
	end
	GunModel.remove(character)
	local part = character:FindFirstChild(partName) :: BasePart?
	if not t or not part then
		return
	end
	local gun = t:Clone()
	local pivot = gun:GetPivot()
	for _, d in gun:GetDescendants() do
		if d:IsA("BasePart") then
			local w = Instance.new("Weld")
			w.Name = "GunWeld"
			w.Part0 = part
			w.Part1 = d
			w.C0 = offset
			w.C1 = pivot:ToObjectSpace(d.CFrame):Inverse()
			w.Parent = d
		end
	end
	gun:SetAttribute("WeaponId", def.Id)
	gun:SetAttribute("On", partName)
	gun.Parent = character
	if Config.Weapons.Debug then
		print(`[GunModel] {character.Name}: {def.Id} -> {partName}`)
	end
end

-- Half size, along the parent's axes, of a box turned by cf (cf only ever turns by 90 deg steps
-- here, so this is exact).
local function extents(cf: CFrame, size: Vector3): Vector3
	local x, y, z = cf.XVector * size.X, cf.YVector * size.Y, cf.ZVector * size.Z
	return Vector3.new(
		math.abs(x.X) + math.abs(y.X) + math.abs(z.X),
		math.abs(x.Y) + math.abs(y.Y) + math.abs(z.Y),
		math.abs(x.Z) + math.abs(y.Z) + math.abs(z.Z)
	) / 2
end

-- A vest part and its weld (Server/Armor welds every part to the torso; C1:Inverse() is where
-- the part sits in the vest's box frame: front -Z, up +Y).
local function vestPart(vest: Instance, name: string): (BasePart?, Weld?)
	local part = vest:FindFirstChild(name, true)
	local weld = part and part:FindFirstChild("VestWeld")
	if part and part:IsA("BasePart") and weld and weld:IsA("Weld") then
		return part, weld
	end
	return nil, nil
end

-- Pouch k's lid flips open about the back-top edge of its box and stays open.
local function openFlap(vest: Instance, k: number, time: number)
	local flap, weld = vestPart(vest, `MagFlap{k}`)
	if not (flap and weld) or vest:GetAttribute(`Open{k}`) == true then
		return
	end
	vest:SetAttribute(`Open{k}`, true)
	local inBox = weld.C1:Inverse()
	local ext = extents(inBox, flap.Size)
	local hinge = CFrame.new(inBox.Position + Vector3.new(0, ext.Y, ext.Z))
	local rest = hinge:Inverse() * inBox
	local w = weld :: Weld
	task.spawn(function()
		local t0 = os.clock()
		repeat
			local u = math.min(1, (os.clock() - t0) / math.max(time, 1e-3))
			u = 1 - (1 - u) * (1 - u) -- fast flick, eases out
			w.C1 = (hinge * CFrame.Angles(FLAP_OPEN * u, 0, 0) * rest):Inverse()
			if u < 1 then
				RunService.Heartbeat:Wait()
			end
		until u >= 1 or not w.Parent
	end)
end

-- A copy of pouch k's mag top, welded in the left hand where the full mag (magInGun: the
-- Magazine part in gun space) will be held, so it comes up out of the pouch with the hand.
-- The pouch's own copy hides (the pouch is empty).
local function takePouchMag(character: Model, vest: Instance, k: number, hand: BasePart, magInGun: CFrame): BasePart?
	local piece, weld = vestPart(vest, `PouchMag{k}`)
	if not (piece and weld) then
		return nil
	end
	local inBox = weld.C1:Inverse()
	local top = inBox.Position + Vector3.new(0, extents(inBox, piece.Size).Y, 0)
	local scale = Config.Weapons.GunScale or 1
	-- where the whole magazine would be if it went on down into the pouch (Pouches rule:
	-- mag top at the piece's top, muzzle direction to the wearer's right)
	local fullMag = CFrame.new(top) * POUCH_ROT * CFrame.new(-MAGWELL * scale) * magInGun
	local held = piece:Clone()
	for _, d in held:GetChildren() do
		if d:IsA("JointInstance") then
			d:Destroy()
		end
	end
	held.Name = "PouchMagHeld"
	held.Transparency = 0 -- (a used pouch counts as refilled)
	local w = Instance.new("Weld")
	w.Part0 = hand
	w.Part1 = held
	w.C0 = MAG_DRAW_IN_HAND * fullMag:Inverse() * inBox
	w.Parent = held
	held.Parent = character
	piece.Transparency = 1
	vest:SetAttribute(`Taken{k}`, true)
	return held
end

-- Reload sounds (tools/reload_sounds.py), played from the server so everyone nearby hears them.
-- Volume / range: Config.Weapons.Sound.Reload / ReloadRange.
local function reloadSound(part: BasePart, name: string)
	local id = (SoundIds :: any)[name]
	local cfg = Config.Weapons.Sound
	if not id or not cfg or not cfg.Enabled or not part.Parent then
		return
	end
	local s = Instance.new("Sound")
	s.SoundId = "rbxassetid://" .. id
	s.Volume = (cfg.Reload or 1) * (cfg.Volume or 1)
	s.PlaybackSpeed = 1 + (math.random() * 2 - 1) * 0.03
	s.RollOffMode = Enum.RollOffMode.InverseTapered
	s.RollOffMinDistance = 5
	s.RollOffMaxDistance = cfg.ReloadRange or 60
	s.Parent = part
	s:Play()
	game:GetService("Debris"):AddItem(s, 2)
end

-- Plays the magazine swap on the real Magazine part, in time with the reload clip played at
-- `speed` (clip length / reload time). Old mag is dropped to the floor. The new one comes out
-- of the next vest pouch when fromPouches (Shared/Armor/Pouches: the lid flips open and stays
-- open), else from the left hip; it's pushed into the well, then slapped home.
function GunModel.reloadMag(character: Model, speed: number, fromPouches: boolean?)
	local gun = character:FindFirstChild("Gun")
	local mag = gun and gun:FindFirstChild("Magazine", true)
	local weld = mag and mag:FindFirstChild("GunWeld")
	local hand = character:FindFirstChild("LeftHand")
	if not (mag and mag:IsA("BasePart") and weld and weld:IsA("Weld") and hand and hand:IsA("BasePart")) then
		return
	end
	local gunPart0, gunC0, gunC1 = weld.Part0, weld.C0, weld.C1
	if gunPart0 == hand then
		return -- already mid-reload
	end
	local token = (mag:GetAttribute("Reload") or 0) + 1
	mag:SetAttribute("Reload", token)
	-- the pouch this reload takes from (the client picked its clip the same way)
	local vest = character:FindFirstChild("ArmorVest")
	local pouch = if fromPouches then Pouches.next(character) else nil
	if vest and pouch then
		vest:SetAttribute("NextPouch", Pouches.after(pouch))
	end
	local held: BasePart? = nil
	local function dropHeld()
		if held then
			held:Destroy()
			held = nil
		end
	end
	local function at(t: number, fn: () -> ())
		task.delay(t / speed, function()
			if weld.Parent and mag.Parent and gun.Parent == character and mag:GetAttribute("Reload") == token then
				fn()
			end
		end)
	end
	at(RELOAD_BEATS.grab, function()
		weld.Part0, weld.C0, weld.C1 = hand, MAG_IN_HAND, CFrame.new()
		reloadSound(mag, "ReloadMagOut")
	end)
	at(RELOAD_BEATS.drop, function()
		-- the empty mag falls away
		local old = mag:Clone()
		for _, d in old:GetChildren() do
			if d:IsA("JointInstance") then
				d:Destroy()
			end
		end
		old.CFrame = mag.CFrame
		old.Anchored = false
		old.CanCollide = true
		old.Massless = false
		old.Parent = workspace
		old.AssemblyLinearVelocity = mag.AssemblyLinearVelocity + Vector3.new(0, -4, 0)
		game:GetService("Debris"):AddItem(old, 10)
		mag.Transparency = 1
	end)
	if vest and pouch then
		at(RELOAD_BEATS.flap, function()
			if vest.Parent == character then
				openFlap(vest, pouch, FLAP_TIME / speed)
			end
		end)
		at(RELOAD_BEATS.take, function()
			if vest.Parent == character then
				held = takePouchMag(character, vest, pouch, hand, gunC1:Inverse())
			end
		end)
	end
	-- the full mag in the hand: out of the pouch (taking over from the piece) or off the hip
	at(if vest and pouch then RELOAD_BEATS.swap else RELOAD_BEATS.take, function()
		dropHeld()
		weld.Part0, weld.C0, weld.C1 = hand, MAG_DRAW_IN_HAND, CFrame.new()
		mag.Transparency = 0
	end)
	at(RELOAD_BEATS.seated - 0.02, function()
		reloadSound(mag, "ReloadMagSeat")
	end)
	at(RELOAD_BEATS.partial, function()
		-- in the well, not quite home; the hand lets go to slap it
		weld.Part0, weld.C0, weld.C1 = gunPart0, gunC0 * CFrame.new(0, -PARTIAL, 0), gunC1
	end)
	at(RELOAD_BEATS.seated, function()
		weld.Part0, weld.C0, weld.C1 = gunPart0, gunC0, gunC1
	end)
	-- whatever happens, the mag ends up back in the gun
	local function restore()
		dropHeld()
		if weld.Parent then
			weld.Part0, weld.C0, weld.C1 = gunPart0, gunC0, gunC1
		end
		mag.Transparency = 0
	end
	restoreMag[mag] = restore
	at(RELOAD_BEATS.length, restore)
	task.delay(RELOAD_BEATS.length / speed, function()
		if restoreMag[mag] == restore then
			restoreMag[mag] = nil
		end
	end)
end

-- Reload cut short (holstered, switched weapon): the magazine snaps back into the gun now.
function GunModel.cancelReload(character: Model)
	local gun = character:FindFirstChild("Gun")
	local mag = gun and gun:FindFirstChild("Magazine", true)
	local restore = mag and restoreMag[mag]
	if mag and restore then
		restoreMag[mag] = nil
		mag:SetAttribute("Reload", (mag:GetAttribute("Reload") or 0) + 1) -- skips the beats left
		restore()
	end
end

function GunModel.hold(character: Model, def)
	attach(character, def, "RightHand", HAND_TO_GUN)
end

function GunModel.sling(character: Model, def)
	attach(character, def, "UpperTorso", BACK)
end

return GunModel
