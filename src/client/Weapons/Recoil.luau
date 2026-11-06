--[[
	Camera recoil, GTA 5 style (Dev 2026-11-06: "copy the gta pattern and feel, little shakes").

	Every shot:
	  * climb: the view creeps up a little per shot and stays there (you pull the mouse down to
	    hold a spray on target), with a small random sideways drift that leans right;
	  * kick: a quick snap up that springs back within ~0.1 s, so each shot punches;
	  * shake: a tiny random wobble in yaw and roll that dies out fast.
	After a burst a share of the climb settles back by itself, like GTA.

	Aiming has less recoil than firing from the hip. Numbers live in the weapon def
	(def.Recoil); missing fields fall back to DEFAULT.

	The camera script rebuilds the view each frame from the camera's current look direction,
	so climb and kick are applied as per-frame changes in pitch / yaw (they stick, and mouse
	look keeps working). Roll is rebuilt away by the camera script every frame, so it is put
	back in absolute each frame.
]]

local RunService = game:GetService("RunService")

local Recoil = {}

local DEFAULT = {
	Climb = 0.45, -- degrees the view creeps up per shot
	Side = 0.22, -- degrees of random sideways drift per shot
	SideBias = 0.35, -- share of the drift that leans right (GTA rifles pull up-right)
	Kick = 1.1, -- degrees of the snap up on each shot (springs back)
	Shake = 0.5, -- degrees of the yaw / roll wobble
	FirstShot = 1.4, -- first shot of a burst kicks this much harder
	Settle = 0.45, -- share of a burst's climb that drifts back after you stop
	HipScale = 1.35, -- firing from the hip
	AimScale = 0.75, -- aiming
}

local rad = math.rad
local rng = Random.new()

-- climb (sticks): target and how much of it is on the camera so far
local climbTarget = Vector2.zero -- (pitch, yaw) radians
local climbApplied = Vector2.zero
local burstClimb = Vector2.zero
local lastShot = -1
local settling = false
local settleShare = DEFAULT.Settle

-- springs (pitch kick, yaw shake, roll shake): x, v
local kick = { x = 0, v = 0 }
local yaw = { x = 0, v = 0 }
local roll = { x = 0, v = 0 }
local springApplied = Vector2.zero -- (pitch, yaw) already put on the camera

local function stepSpring(s, k: number, damp: number, dt: number)
	-- semi-implicit Euler, sub-stepped so a long frame can't blow it up
	local n = math.max(1, math.ceil(dt / (1 / 240)))
	local h = dt / n
	for _ = 1, n do
		s.v += (-k * s.x - damp * s.v) * h
		s.x += s.v * h
	end
end

function Recoil.kick(def, aiming: boolean)
	local r = def.Recoil or {}
	local function get(key: string): number
		local v = r[key]
		return if v ~= nil then v else DEFAULT[key]
	end
	local scale = if aiming then get("AimScale") else get("HipScale")
	local now = os.clock()
	local first = now - lastShot > 0.35
	lastShot = now
	settling = false
	settleShare = get("Settle")
	if first then
		burstClimb = Vector2.zero
	end

	local bias = get("SideBias")
	local side = rng:NextNumber(-1, 1) * (1 - bias) + bias * rng:NextNumber(0, 1)
	-- yaw: + turns left in Roblox (angle about +Y), so the rightward lean is negative
	local add = Vector2.new(rad(get("Climb")), -rad(get("Side")) * side) * scale
	climbTarget += add
	burstClimb += add

	local k = rad(get("Kick")) * scale * (if first then get("FirstShot") else 1)
	kick.v += k * 38
	local shake = rad(get("Shake")) * scale
	yaw.v += rng:NextNumber(-1, 1) * shake * 30
	roll.v += rng:NextNumber(-1, 1) * shake * 45
end

function Recoil.start()
	RunService:BindToRenderStep("WeaponRecoil", Enum.RenderPriority.Camera.Value + 1, function(dt)
		local cam = workspace.CurrentCamera
		if not cam then
			return
		end
		dt = math.min(dt, 0.1)
		local now = os.clock()

		-- after a burst, part of the climb drifts back down
		if not settling and lastShot > 0 and now - lastShot > 0.18 then
			settling = true
			climbTarget -= burstClimb * settleShare
			burstClimb = Vector2.zero
		end

		-- climb: fast while firing, slow and soft while settling
		local rate = if settling then 5 else 30
		local nextClimb = climbApplied + (climbTarget - climbApplied) * (1 - math.exp(-rate * dt))
		local dClimb = nextClimb - climbApplied
		climbApplied = nextClimb
		-- keep the numbers small: what is fully applied no longer matters
		if (climbTarget - climbApplied).Magnitude < 1e-5 then
			climbTarget, climbApplied = Vector2.zero, Vector2.zero
		end

		stepSpring(kick, 420, 26, dt) -- snappy, settles in about 0.12 s
		stepSpring(yaw, 520, 30, dt)
		stepSpring(roll, 480, 24, dt)
		local springNow = Vector2.new(kick.x, yaw.x)
		local dSpring = springNow - springApplied
		springApplied = springNow

		local dPitch = dClimb.X + dSpring.X
		local dYaw = dClimb.Y + dSpring.Y
		if math.abs(dPitch) < 1e-6 and math.abs(dYaw) < 1e-6 and math.abs(roll.x) < 1e-5 then
			return
		end

		local cf = cam.CFrame
		local _, curYaw, _ = cf:ToEulerAnglesYXZ()
		local look = cf.LookVector
		local curPitch = math.asin(math.clamp(look.Y, -1, 1))
		local pitch = math.clamp(curPitch + dPitch, -rad(80), rad(80))
		cam.CFrame = CFrame.new(cf.Position) * CFrame.fromEulerAnglesYXZ(pitch, curYaw + dYaw, roll.x)
	end)
end

return Recoil
