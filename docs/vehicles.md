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

## Real models (next step)

A real car model needs the same layout the placeholder has (see the top of `Builder.luau`):
`Chassis` (collision box, PrimaryPart) with `Wheel<FL|FR|RL|RR>` attachments at the
suspension tops, `DriverSeat` (VehicleSeat), and wheel meshes named `Wheel_<FL|...>` welded to
`Chassis` with a Weld called `Mount`. Set `Model` in the Def to its name in `Shared.ModelIds`;
Builder then loads the mesh as the body instead of the blocks (that hookup is still to do).

## Ideas for later

Passenger seats, door/enter animations, engine sounds and gears, headlights at night,
damage and health, fuel, car horn, NPC traffic, garages/owned cars, drive-by shooting.
