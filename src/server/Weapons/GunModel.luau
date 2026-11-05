--[[
	Puts a weapon's 3D model on the character (server side, so everyone sees it).

		GunModel.hold(character, def)    -- welded in the right hand (the animations aim it)
		GunModel.sling(character, def)   -- on the back (holstered)
		GunModel.remove(character)

	The model is loaded by id from Shared.ModelIds[def.Model] and scaled by
	Config.Weapons.GunScale. Its origin is the pistol-grip hold point, muzzle toward -Z.
	HAND_TO_GUN must match art/anim/gun.py (it prints the numbers): the animations are solved
	for exactly this hand offset, so the left hand lands on the handguard.
	A "Muzzle" attachment is added at the flash hider for tracers and effects.
]]

local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local ModelIds = require(Shared:WaitForChild("ModelIds"))

local GunModel = {}

-- RightHand -> gun origin (from art/anim/gun.py)
local HAND_TO_GUN = CFrame.new(0, -0.158, 0, 1, 0, 0, 0, 0.3746, 0.9272, 0, -0.9272, 0.3746)
-- Muzzle at scale 1 (studs, gun space), from the imported model
local MUZZLE = Vector3.new(0, 0.269, -1.634)
-- On the back: flat against the back plate, muzzle up over the left shoulder.
local BACK = CFrame.fromMatrix(Vector3.new(0.21, -0.28, 0.78), Vector3.new(0, 0, 1), Vector3.new(-0.8, -0.6, 0), Vector3.new(0.6, -0.8, 0))

-- Reload: the magazine part goes into the left hand on the beats of Weapon_Rifle_Reload
-- (art/anim/gun.py RELOAD / MAG_IN_HAND; seconds at playback speed 1).
local MAG_IN_HAND = CFrame.new(0.3712, -0.0027, 0.0795, 0.4226, 0.9063, 0, -0.8517, 0.3971, -0.342, -0.31, 0.1445, 0.9397)
local RELOAD_BEATS = { grab = 0.45, drop = 0.8, new = 1.12, seated = 1.62, length = 2.3 }
GunModel.ReloadLength = RELOAD_BEATS.length

local templates: { [string]: Model | false } = {}

local function template(name: string): Model?
	if templates[name] ~= nil then
		return templates[name] or nil
	end
	local id = ModelIds[name]
	if not id then
		templates[name] = false
		return nil
	end
	local ok, container = pcall(InsertService.LoadAsset, InsertService, id)
	if not ok then
		warn(`[GunModel] could not load {name} ({id}): {container}`)
		templates[name] = false
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
	end
	templates[name] = model
	return model
end

function GunModel.remove(character: Model)
	local old = character:FindFirstChild("Gun")
	if old then
		old:Destroy()
	end
end

local function attach(character: Model, def, partName: string, offset: CFrame)
	GunModel.remove(character)
	local t = def and def.Model and template(def.Model)
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
	gun.Parent = character
end

-- Plays the magazine swap on the real Magazine part, in time with the reload clip played at
-- `speed` (clip length / reload time). Old mag is dropped to the floor; the fresh one comes
-- from the vest and goes back into the gun.
function GunModel.reloadMag(character: Model, speed: number)
	local gun = character:FindFirstChild("Gun")
	local mag = gun and gun:FindFirstChild("Magazine", true)
	local weld = mag and mag:FindFirstChild("GunWeld")
	local hand = character:FindFirstChild("LeftHand")
	if not (mag and mag:IsA("BasePart") and weld and weld:IsA("Weld") and hand) then
		return
	end
	local gunPart0, gunC0, gunC1 = weld.Part0, weld.C0, weld.C1
	if gunPart0 == hand then
		return -- already mid-reload
	end
	local token = (mag:GetAttribute("Reload") or 0) + 1
	mag:SetAttribute("Reload", token)
	local function at(t: number, fn: () -> ())
		task.delay(t / speed, function()
			if weld.Parent and mag.Parent and gun.Parent == character and mag:GetAttribute("Reload") == token then
				fn()
			end
		end)
	end
	at(RELOAD_BEATS.grab, function()
		weld.Part0, weld.C0, weld.C1 = hand, MAG_IN_HAND, CFrame.new()
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
	at(RELOAD_BEATS.new, function()
		mag.Transparency = 0 -- fresh mag out of the vest pouch
	end)
	at(RELOAD_BEATS.seated, function()
		weld.Part0, weld.C0, weld.C1 = gunPart0, gunC0, gunC1
	end)
	-- whatever happens, the mag ends up back in the gun
	at(RELOAD_BEATS.length, function()
		weld.Part0, weld.C0, weld.C1 = gunPart0, gunC0, gunC1
		mag.Transparency = 0
	end)
end

function GunModel.hold(character: Model, def)
	attach(character, def, "RightHand", HAND_TO_GUN)
end

function GunModel.sling(character: Model, def)
	attach(character, def, "UpperTorso", BACK)
end

return GunModel
