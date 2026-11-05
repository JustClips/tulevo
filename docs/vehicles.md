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

## Ideas for later

Passenger seats, door/enter animations, engine sounds and gears, headlights at night,
damage and health, fuel, car horn, NPC traffic, garages/owned cars, drive-by shooting.
