-- Sport bike (our own S1000RR-style design, no brand marks). Model: art/models/BikeRide, the light
-- copy of the Superbike (art/blender/superbike/assemble.py --lite). Driven by Vehicles/BikePhysics
-- (Kind = "Bike"): two ray wheels, kept upright by an AlignOrientation; the body, rider and wheels
-- lean into turns as a visual (Client/Vehicles/Bike). Rider clips: art/anim/bike.py, which must use
-- the same S and Steering.MaxAngle as here.
-- Positions are relative to the Chassis centre (-Z = front); the Chassis centre is 0.55 m above the
-- ground between the axles. Bike points are Blender meters (X = bike's left, Y = back, Z = up).
local S = 4.4 -- studs per meter, same as the hypercar (blocky avatars need the bigger vehicles)
local GROUND = -0.55 * S
local SUS_LENGTH = 0.30 * S
local FREQUENCY = 2.4
local REST = SUS_LENGTH - 9.81 * 20 / (2 * math.pi * FREQUENCY) ^ 2 -- Suspension.Length - static sag
local FRONT_R, REAR_R = 0.2999 * S, 0.3204 * S -- tyre radius = hub height

return {
	Id = "Superbike",
	Name = "Vento RR",
	Kind = "Bike",
	Model = "BikeRide", -- name in Shared.ModelIds

	Size = Vector3.new(0.55 * S, 0.5 * S, 2.0 * S), -- collision box, 0.30 .. 0.80 m above the ground
	DriverSeat = Vector3.new(0, GROUND + 0.845 * S, 0.29 * S), -- top of the seat part = where the rider sits
	ExitSide = -1, -- get on and off on the left, like a real bike (side stand side)
	-- where you stand after getting off (HumanoidRootPart, chassis space): where the Dismount clip ends
	ExitOffset = Vector3.new(-0.55 * S, GROUND + 3.2, 0.04 * S),

	Wheels = {
		Radius = FRONT_R,
		RearRadius = REAR_R,
		-- suspension tops, straight above each hub
		F = Vector3.new(0, GROUND + FRONT_R + REST, -0.7205 * S),
		R = Vector3.new(0, GROUND + REAR_R + REST, 0.7205 * S),
	},

	Suspension = {
		Length = SUS_LENGTH,
		Frequency = FREQUENCY,
		Damping = 0.6,
	},

	Engine = {
		Drive = "Rear",
		Accel = 62,
		MaxSpeed = 175, -- studs/s
		ReverseSpeed = 6, -- pushing it back with your feet
		Brake = 125,
		Coast = 6,
	},

	Steering = {
		MaxAngle = 24, -- bar lock at walking speed; at speed the lean limit (below) caps the turn
		Speed = 3.2, -- radians/s
		ReturnSpeed = 5,
	},

	Lean = {
		Max = 48, -- degrees; the hardest turn is the one that needs this lean (Gravity x tan(Max))
		Rate = 140, -- degrees/s the body can roll
		Parked = 5, -- degrees it rests on the side stand
	},

	Grip = {
		Rate = 14,
		Friction = 1.6,
		Front = 1,
		Rear = 1,
		Handbrake = 0.45, -- Space = rear brake: the back steps out a little
	},

	-- How the model's parts move (Server/Vehicles/BikeBuilder + Client/Vehicles/Bike).
	-- Blender meters, see art/models/BikeRide/meta.json ("points_m", "groups").
	Rig = {
		Scale = S,
		Ground = GROUND,
		Wheelbase = 1.441,
		FrontAxle = Vector3.new(0, -0.7205, 0.2999),
		RearAxle = Vector3.new(0, 0.7205, 0.3204),
		SwingPivot = Vector3.new(0, 0.12, 0.42),
		StandPivot = Vector3.new(0.112, 0.055, 0.30),
		StandAngle = 78, -- degrees the side stand swings down
		Rake = 23.1, -- steering axis tilt (degrees back from vertical)
		SteerGroundY = -0.8144, -- the steering axis meets the ground here
		Seat = Vector3.new(0, 0.29, 0.845),
		-- parts that move together; everything else is the rigid body
		Groups = {
			Steer = { "ForkOuter", "TopClamp", "BottomClamp", "Bars", "Grips", "Controls", "Levers" },
			Fork = {
				"ForkInner",
				"ForkFeet",
				"Mudguard",
				"MudguardFins",
				"FrontCaliperL",
				"FrontCaliperR",
				"FrontPadL",
				"FrontPadR",
			},
			FrontWheel = {
				"FrontTyre",
				"FrontRim",
				"FrontValve",
				"FrontRotorL",
				"FrontRotorR",
				"FrontCarrierL",
				"FrontCarrierR",
			},
			Swing = {
				"Swingarm",
				"ChainSlider",
				"Hugger",
				"HuggerTabs",
				"RearCaliper",
				"RearPad",
				"RearBracket",
				"OuterPlatesL",
				"OuterPlatesR",
				"InnerPlates",
				"Rollers",
				"Pins",
				"Seals",
			},
			RearWheel = { "RearTyre", "RearRim", "RearValve", "RearRotor", "RearSprocket" },
			Stand = { "SideStand" },
		},
	},

	-- rider clips (Shared.AnimIds), made by art/anim/bike.py
	Anims = {
		Ride = "Tulevo_BikeRide",
		SteerLeft = "Tulevo_BikeSteerLeft",
		SteerRight = "Tulevo_BikeSteerRight",
		LeanLeft = "Tulevo_BikeLeanLeft",
		LeanRight = "Tulevo_BikeLeanRight",
		Tuck = "Tulevo_BikeTuck",
		Stop = "Tulevo_BikeStop",
		Mount = "Tulevo_BikeMount",
		Dismount = "Tulevo_BikeDismount",
	},
}
