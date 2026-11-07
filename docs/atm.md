# ATMs

The Arkwell Bank has a real 3D double ATM on its left pylon (model `ArkwellAtm`), replacing the
old printed panel. No banking yet; this is the hook a bank UI will use.

## Model

- `python3 tools/atm_textures.py` draws the sheets (brushed steel, keypad legends, screen, labels,
  sign) into `art/blender/atm/tex`.
- `art/blender/atm/build_atm.py` builds it (Blender 5.2, or the `bpy` wheel), in studs.
  Pipeline: `tools/install_model.py OUT` -> `upload_textures.py` -> `upload_models.py` ->
  `grant_universe.py ArkwellAtm` -> `city_colliders.py ArkwellAtm` -> `build_city_map.py`.
- Placed by `tools/build_city_map.py` (`BUILDINGS`, at 66, 1.6, -68.12 on the bank plinth).
  Collision is two hand boxes (surround + canopy).

## Hook for the bank UI

`src/server/Atms.server.luau` decorates every `Atm<N>Screen` part in a city model once
`Server/CityBuildings` sets `CityReady`:

| What | Where |
| --- | --- |
| Display | `SurfaceGui "Display"` on the screen face (unlit), `ImageLabel "Idle"` = welcome screen |
| Prompt | `Attachment "AtmUse"` > `ProximityPrompt "AtmPrompt"` ("Use ATM", E, 7 studs) |
| Id | screen attribute `AtmId` (e.g. `ArkwellAtm_1`), CollectionService tag `Atm` |
| Client event | `ReplicatedStorage.AtmRemotes.Open` fires `(atmId, screenPart)` to the user |
| Server event | `ReplicatedStorage.AtmRemotes.Used` (BindableEvent) `(player, atmId, screenPart)` |

Money itself is `Server/Money.luau` (`deposit` / `withdraw` between Cash and Bank, see money.md).
To add more ATMs elsewhere, place another `ArkwellAtm` (or any model with `Atm<N>Screen` parts).
