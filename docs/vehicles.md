# Vehicle system

Basic driving for now, laid out so more car features and real models slot in later.
Cars drive on ray-cast wheels: each wheel shoots a ray down, a spring pushes the car up,
and engine, brakes and tyre grip push it along. One physics module drives every car; each
car is just a data file.

## Layout

| Where | What |
|---|---|
| `src/shared/Vehicles/Defs/*.luau` | One file per car: size, seat, wheels, suspension, engine, steering, grip (data only) |
| `src/shared/Vehicles/init.luau` | Registry: `Vehicles.get(id)`, `Vehicles.all()`, `Vehicles.modelOf(part)` |
| `src/shared/Vehicles/Physics.luau` | The driving model (suspension, engine/brake/reverse, steering, grip, handbrake, auto-unflip) |
| `src/server/Vehicles/Builder.luau` | Builds a car model from its Def (block placeholder until the car has a mesh) |
| `src/server/Vehicles/VehicleService.luau` | Spawning, getting in/out, hands the car to the driver's client, runs parked cars |
| `src/server/VehiclesRunner.server.luau` | Starts it and parks `Config.Vehicles.TestCars` next to the spawn |
| `src/client/Vehicles/init.luau` | Runs the physics for the car you drive, puts weapons away |
| `src/client/Vehicles/Input.luau` | Driving controls |
| `src/client/Vehicles/Wheels.luau` | Wheel visuals on every car (suspension travel, steering, spin) |
| `src/client/Vehicles/Cockpit.luau` | Real models: steering wheel, pedals, body lean, driver's legs |
| `src/client/Vehicles/Bike.luau` | Motorbikes (see below) |
| `src/client/Movement/Moves/Seated.luau` | Sitting beats every on-foot move |

Who simulates: the driver's client owns the car while driving (no input lag), the server
owns and simulates parked cars. Model attribute `DriverId` = the driver's UserId.

## Controls

Get in: walk to the driver's door, F (gamepad Y, tap the prompt on phones). Get out: F / Y / Exit.

| | Keyboard | Gamepad | Phone |
|---|---|---|---|
| Gas | W | RT | stick up |
| Brake / reverse | S | LT | stick down |
| Steer | A / D | left stick | stick sideways |
| Handbrake | Space | RB (or A) | Brake button |

## Add a car

Copy `Defs/Sedan.luau`, change `Id`, `Name`, size, wheel positions and tuning, and add it to
`Config.Vehicles.TestCars` to try it.

## Real models

A car gets a real mesh by setting `Model` (its name in `Shared.ModelIds`) and a `Rig` table in
its Def (see `Defs/Hypercar.luau`). The mesh is a GLB in `art/models/<Name>/` uploaded by
`tools/upload_models.py`; until it has an id the car keeps the block placeholder.

The GLB needs separate objects named `Body`, `Wheel_FL/FR/RL/RR` (and optionally
`Caliper_<FL|...>`, `Glass`, `Interior`, `Door_L/R`, `SteeringWheel`, `Pedal_Gas`,
`Pedal_Brake`). Builder measures where the importer put the car from the four wheels, scales it
to studs and welds every part on: wheels and calipers on `Mount` welds (`Vehicles/Wheels`
moves them; calipers don't spin), everything else on `BodyRoot`, which hangs off `Chassis` by a
Weld called `Lean`. `client/Vehicles/Cockpit.luau` then turns the steering wheel with the
steering, presses the pedals with throttle/brake, leans the body out of turns and dips it under
braking, and straightens the driver's knees in low cars (`Rig.KneeLift`). Other players' cars
use the seat's `ThrottleFloat`/`SteerFloat`, which the driver's client sets.

`Rig` points are Blender meters (X = car's left, Y = back, Z = up, origin on the ground between
the axles); `Rig.Scale` studs per meter, `Rig.Ground` = chassis-space height of the ground.

Hypercar ("Veloce H9", `art/blender/hypercar`): open-top mid-engine two-seater, about 43k
triangles over 17 parts (Body 17k, the biggest).

## Motorbikes

A Def with `Kind = "Bike"` (see `Defs/Superbike.luau`, the "Vento RR") is a motorbike. Same
spawning, prompt ("Ride", on the left), speed checks and controls as the cars, but:

| Where | What |
|---|---|
| `src/shared/Vehicles/BikePhysics.luau` | Two ray wheels on the centre line (rear drive, both brake), an AlignOrientation (`Chassis/Upright`) rolls the chassis back to the ground's up so it never falls over. Steering is capped by the lean limit: at speed a turn never needs more sideways grip than Gravity x tan(`Lean.Max`). |
| `src/shared/Vehicles/BikeRig.luau` | Hinge points in chassis space (steering axis, axles, swingarm pivot, side stand, seat) from `Def.Rig` |
| `src/server/Vehicles/BikeBuilder.luau` | Builds the bike from the uploaded `BikeRide` model: groups from `Rig.Groups` ride on invisible hinge parts (`SteerRoot`, `ForkRoot`, `FrontHub`, `SwingRoot`, `RearHub`, `StandRoot`); the seat is on `BodyRoot`, so the rider leans with the bike. Paints parts from `ModelLooks` / `TextureIds`. |
| `src/client/Vehicles/Bike.luau` | Every bike in view: lean into turns (from speed x turn rate), bars + forks turn about the rake axis, forks slide and the swingarm swings with the suspension, wheels spin, a parked bike drops its side stand and rests on it. Your rider: Mount clip, then a weighted blend of Ride / Stop / Tuck / SteerLeft / SteerRight / LeanLeft / LeanRight, Dismount before the Exit remote. |

The rider: `VehicleService` sets the SeatWeld so the HumanoidRootPart is 1 stud over the seat point
(the clips are posed from there), makes the rider massless and puts them in collision group
`Rider` (collides with nothing) until they get off. Getting off (F / Y) plays Dismount (the bike
holds still) and then fires Exit; the server stands you at `Def.ExitOffset`, where the clip ends.
Above walking pace F gets you off at once.

Rider clips: `python3 art/anim/bike.py` (writes `art/out/anims/Tulevo_Bike*.rbxmx`), then
`python3 tools/upload_anims.py`. `S` and `STEER_LOCK` there must match the Def's `Rig.Scale` and
`Steering.MaxAngle`. The blocky rig's arms only reach about 1.5 studs, so the rider sits forward with
the chest down (a sport-bike crouch), and the legs can't reach the ground, so the feet stay on the pegs.

Model: `art/blender/superbike/assemble.py --lite` (about 159k triangles; the full `Superbike` is
for the Showcase), uploaded by `tools/upload_models.py`.

## Ideas for later

Passenger seats, door/enter animations, engine sounds and gears, headlights at night,
damage and health, fuel, car horn, NPC traffic, garages/owned cars, drive-by shooting.
