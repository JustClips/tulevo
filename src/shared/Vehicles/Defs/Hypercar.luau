-- Open-top mid-engine hypercar (our own design, no real brand). Model: art/models/Hypercar
-- (built by art/blender/hypercar). Positions are relative to the Chassis centre; -Z is the front.
-- Sizes come from the Blender model (meters) times S studs per meter; ground at Y = Rig.Ground.
-- S is bigger than the 3.6 the weapons use: blocky Roblox avatars make a true-to-scale
-- hypercar look tiny, so the whole car is scaled up (change S to resize everything).
local S = 4.4
local GROUND = -0.64 * S -- chassis-space height of the ground under the car at rest
local HUB_Y = GROUND + 0.36 * S -- wheel centre at rest
local SUS_LENGTH = 0.39 * S
local REST = SUS_LENGTH - 9.81 * 20 / (2 * math.pi * 2.6) ^ 2 -- Suspension.Length - static sag

return {
	Id = "Hypercar",
	Name = "Veloce H9",
	Model = "Hypercar", -- name in Shared.ModelIds

	Size = Vector3.new(1.83 * S, 0.5 * S, 4.44 * S),
	DriverSeat = Vector3.new(-0.38 * S, GROUND + 0.30 * S - 0.2, 0.10 * S), -- left-hand drive, seat part's top on the cushion
	ExitSide = -1,

	Colors = { -- placeholder colours, only used until the model has loaded
		Body = Color3.fromRGB(190, 192, 196),
		Trim = Color3.fromRGB(20, 20, 22),
	},

	Wheels = {
		Radius = 0.36 * S,
		Width = 0.3 * S,
		-- suspension tops, straight above each hub of the model
		FL = Vector3.new(-0.80 * S, HUB_Y + REST, -1.365 * S),
		FR = Vector3.new(0.80 * S, HUB_Y + REST, -1.365 * S),
		RL = Vector3.new(-0.785 * S, HUB_Y + REST, 1.365 * S),
		RR = Vector3.new(0.785 * S, HUB_Y + REST, 1.365 * S),
	},

	Suspension = {
		Length = SUS_LENGTH,
		Frequency = 2.6, -- stiffer than the sedan
		Damping = 0.65,
		AntiRoll = 0.75,
	},

	Engine = {
		Drive = "All",
		Accel = 56,
		MaxSpeed = 165, -- studs/s; the car is drawn bigger than life (S above), so it runs a bit faster
		ReverseSpeed = 28,
		Brake = 130,
		Coast = 5,
	},

	Steering = {
		MaxAngle = 32,
		TopSpeedAngle = 5,
		Speed = 4.5,
		ReturnSpeed = 7,
	},

	Grip = {
		Rate = 14,
		Friction = 1.8,
		Front = 1,
		Rear = 1,
		Handbrake = 0.3,
	},

	-- How the model's parts move (Vehicles/Builder + client Vehicles/Cockpit).
	-- Points are in Blender meters (see art/models/Hypercar/meta.json): X = car's left, Y = back, Z = up.
	Rig = {
		Scale = S,
		Ground = GROUND,
		HubHeight = 0.36,
		Wheelbase = 2.73,
		Glass = { "Glass" },
		ClearGlass = { "LampGlass" },
		SteeringWheel = {
			Part = "SteeringWheel",
			Center = Vector3.new(0.38, -0.36, 0.66),
			Axis = Vector3.new(0, math.cos(math.rad(22)), math.sin(math.rad(22))), -- toward the driver
			MaxTurn = 120, -- degrees at full lock
		},
		Pedals = {
			Gas = { Part = "Pedal_Gas", Pivot = Vector3.new(0.28, -0.93, 0.50) },
			Brake = { Part = "Pedal_Brake", Pivot = Vector3.new(0.43, -0.93, 0.50) },
			Travel = 22, -- degrees fully pressed
		},
		Doors = {
			Door_L = Vector3.new(0.90, -0.86, 0.50), -- hinge (vertical axis); not animated yet
			Door_R = Vector3.new(-0.90, -0.86, 0.50),
		},
		KneeLift = 65, -- degrees the driver's shins swing forward (low seat, legs under the dash)
		Lean = {
			Roll = 3.5, -- max degrees the body leans out of a turn
			Pitch = 2.5, -- max degrees of nose dive / squat
			RollPerAccel = 0.025, -- degrees per stud/s^2 of sideways acceleration
			PitchPerAccel = 0.018,
		},
	},
}
