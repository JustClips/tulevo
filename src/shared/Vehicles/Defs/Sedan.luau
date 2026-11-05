-- Plain 4-door sedan, the first test car. Every number here is a tuning knob.
-- Studs: a character is about 5 tall. Speeds in studs/s (sprint is 20).
-- Positions are relative to the Chassis centre; -Z is the front of the car.
return {
	Id = "Sedan",
	Name = "Sedan",
	Model = nil, -- name in Shared.ModelIds once the real mesh exists; nil = placeholder

	-- collision box and seat
	Size = Vector3.new(6.8, 1.8, 14.5),
	DriverSeat = Vector3.new(-1.35, -0.25, 0.9), -- low, so the head stays under the roof
	ExitSide = -1, -- -1 = driver gets out on the left

	Colors = {
		Body = Color3.fromRGB(38, 70, 120),
		Trim = Color3.fromRGB(28, 28, 32),
	},

	Wheels = {
		Radius = 1.3,
		Width = 1.1,
		-- top of each suspension (wheel hub when fully squashed)
		FL = Vector3.new(-3.15, 0.2, -4.7),
		FR = Vector3.new(3.15, 0.2, -4.7),
		RL = Vector3.new(-3.15, 0.2, 4.5),
		RR = Vector3.new(3.15, 0.2, 4.5),
	},

	Suspension = {
		Length = 2, -- travel in studs
		Frequency = 2.2, -- bounce speed (higher = stiffer)
		Damping = 0.6, -- 0 = bouncy, 1 = no bounce
		AntiRoll = 0.6, -- 0 = lots of body roll in turns
	},

	Engine = {
		Drive = "Rear", -- "Front" | "Rear" | "All"
		Accel = 34, -- studs/s per second from a standstill
		MaxSpeed = 95,
		ReverseSpeed = 26,
		Brake = 95, -- studs/s per second when braking
		Coast = 6, -- slowdown with no pedal pressed
	},

	Steering = {
		MaxAngle = 34, -- degrees at low speed
		TopSpeedAngle = 7, -- degrees at MaxSpeed (stops twitchy high-speed turns)
		Speed = 4, -- radians/s the wheels turn toward the stick
		ReturnSpeed = 6, -- radians/s back to centre when you let go
	},

	Grip = {
		Rate = 12, -- how fast sideways sliding is cancelled (per second)
		Friction = 1.5, -- max sideways force = Friction x wheel load
		Front = 1,
		Rear = 1,
		Handbrake = 0.25, -- rear grip multiplier while the handbrake is held (drifts)
	},
}
