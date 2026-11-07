# Gun shop: Ironwood Arms

A walk-in gun store with an indoor range on Vault Avenue (lot D, west of the Palmview Motel,
`IronwoodArms` in `tools/build_city_map.py`). Original design in the style of a GTA gun shop:
our own name, mark and signs, no real brands or gun makers.

## Building (`art/blender/gunshop/build_gunshop.py`, model `GunShop`)

    python3 tools/gunshop_textures.py          # CC0 scans (git-ignored art/gunshop/src) + printed signs
    blender --background --python art/blender/gunshop/build_gunshop.py -- OUT_DIR [--no-render]
    python3 tools/install_model.py OUT_DIR
    python3 tools/upload_textures.py && python3 tools/upload_models.py && python3 tools/grant_universe.py GunShop
    python3 tools/city_colliders.py GunShop && python3 tools/build_city_map.py

- Store: glass display counter with pistols and price cards, till, slatwall of shotguns, carbines
  and SMGs behind it, glass rifle cabinets (left), ammo shelving and an armor form (right), round
  rifle rack, centre glass case, posters, CCTV, drop ceiling lights.
- Range: steel door `Swing2` and a viewing window, 5 lanes with booths, lane numbers, target
  carriers on rails, overhead baffles, sloped backstop.
- Front door `Swing1` (glass). Both doors use Client/CityDoors.
- Rack carbines reuse our CarbineRifle mesh (decimated, flat colours); the other guns are
  original low-poly models in the script. All `Deco*` parts are walk-through decoration.
- Collision: exact boxes from `tools/city_colliders.py` (`src/server/CityColliders/GunShop.luau`).

## Marker parts

`Spot*` parts are hidden by Server/CityBuildings and read by Server/GunShop:
`SpotBuy` (till, buy prompt), `SpotClerk` (clerk), `SpotCam` + `SpotCamLook` (menu camera).

## Buying (`Server/GunShop.server.luau`, `Client/GunShop.client.luau`)

- E at the till opens a GTA-style menu: categories, then items with prices, description, stat
  bars, picture, cash and bank. Up/Down, Enter (buy), Backspace (back/close); mouse, touch
  (BUY button, X) and gamepad work too. The camera looks at the gun wall while it's open.
- Stock and prices: `Config.GunShop.Stock`. A weapon shows "Out of stock" until it has a model in
  `Shared.ModelIds`; a weapon you already carry shows "Owned".
- The server checks everything: menu opened at the till, still near it, alive and not knocked,
  rate limit, price from Config. Goods go in first through InventoryService (a full bag costs
  nothing), then the money is taken: cash first, the rest from the bank (`PayFromBank`).
- Remotes: `ReplicatedStorage.GunShopRemotes` (Open, Buy, Close).
