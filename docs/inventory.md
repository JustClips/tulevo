# Inventory

N opens the window (phone: Bag button). Roblox's default backpack bar is off.

| Where | What |
|---|---|
| `src/shared/Items/Defs.luau` | **Every plain item, one row each** (food, kits, ammo): Name, Description, Kind, Weight (kg), Cells (wide x tall), Stack, Model, Use |
| `src/shared/Items/init.luau` | The registry: merges Defs + weapons + armor into one list with the same fields, fills in the picture (`Icon`), and stops the game with a clear error if a definition is wrong |
| `src/shared/Items/Actions.luau` | Use actions an item can have (Heal, Drink, Equip, Wear) and their tooltip label |
| `src/server/Inventory/ItemUse.luau` | What each server action does (`can` / `apply`) |
| `src/shared/Items/Grid.luau` | Placing maths shared by server and client: footprints, overlaps, first free spot |
| `src/shared/Weapons/Defs/*.luau` | Each weapon's item fields: `Weight`, `Cells` (carbine 4 x 2), `Description`, `Ammo` (the item it reloads from) |
| `src/shared/Armor/init.luau` | Each armor's item fields: `Weight`, `Cells` (vest 2 x 2), `DisplayName`, `Description` |
| `Config.Inventory` | Grid sizes (Inventory 5 x 14, Backpack 4 x 4) and weight limits (30 kg, 10 kg), starting items, ground / pickup range, dropped item lifetime |
| `src/server/Inventory/InventoryService.luau` | Server-owned inventories, move / stack / swap with weight checks, drop to the ground, pick up, the Armor slot |
| `src/server/Inventory/ItemModels.luau` | Loads every item's model into `ReplicatedStorage.ItemModels` (inventory icons, dropped items) |
| `src/client/Inventory.client.luau` | The window: layout, item pictures, drag and drop, hover info, Ground list |
| `art/icons/` | ForgeGUI UI icons (`gen.py` -> `raw/`, `proc.py` -> white `out/`), uploaded by `tools/upload_icons.py` into `Shared/IconIds` |
| `art/items/out/` | Item pictures rendered from `art/models/*.glb` by `tools/item_icons/render.js` (three.js in the built-in Chromium, at each item's Cells shape, 160 px a cell), uploaded by `tools/upload_icons.py --set items` into `Shared/ItemIconIds`. Items without a picture show their live 3D model (pixelated: ViewportFrames have no anti-aliasing) |

## Adding an item

1. Add a row to `src/shared/Items/Defs.luau` (copy Mead): Name, Description, Kind, Weight, Cells,
   Stack, and `Use = { Action = "Heal", Amount = 25, Time = 3 }` if it can be used.
2. If it has a 3D model: upload it (`tools/upload_models.py`, key in `Shared.ModelIds`), set
   `Model` / `ModelScale`, then render + upload its picture (`tools/item_icons/render.js`,
   `tools/upload_icons.py --set items`). Without one it shows its name and lies on the ground
   as a small box.
3. A new kind of use: add it to `Items/Actions.luau` and a `can` / `apply` pair with the same
   name in `Server/Inventory/ItemUse.luau`.

Give it in code with `InventoryService.add(player, id, count)` or put it on the ground with
`InventoryService.spawnPickup(id, count, cframe)`.

## Using items

Right-click or double-click (double-tap on phones) an item in the window, or press its quick
slot key (1-3). Guns come out / go on your back, a vest goes on (on the Armor slot: comes off),
food and first aid are used by the server after their `Use.Time` with a bar above the quick
bar. A use stops if you're knocked down, take a gun out, or the item leaves your bag. A gun in
your hands goes on your back first.

Use animations: `art/anim/use_items.py` makes Tulevo_DrinkBottle (mead), Tulevo_DrinkCan
(chaser) and Tulevo_Medkit (first-aid kit, held by its handle in the left hand) and writes
`src/shared/Items/Holds.luau` (where the real model sits in the hand); upload with
`tools/upload_anims.py`. An item names its clip with `Use.Anim`; the client plays it stretched
to `Use.Time` and the server welds the item's model (`HeldItem`) to the hand meanwhile. Refusals ("Already at
full health") show in the same spot.

## Ammo

A gun with `Ammo = "RifleAmmo"` has no spare bullets of its own: the number next to the
magazine on the ammo HUD is the Rifle ammo you carry, and a reload takes rounds out of the bag
(stacks of 90, 0.012 kg a round). The gun's `ReserveAmmo` is how much ammo you start with.
The magazine stays with the gun when it's dropped. Guns without `Ammo` (the Studio test guns)
keep the old built-in spare bullets.

## Rules

Everyone starts with the Carbine Rifle (`Config.Weapons.DefaultLoadout`) and its 150 rounds of
Rifle ammo, a mead, a chaser and a first-aid kit in the inventory, and the armor vest worn (Armor slot).

- Items cover several cells and sit at their top-left cell. While dragging, a green box shows
  where the item lands (red = overlaps, out of the grid or too heavy) and R turns it 90 degrees
  (stored as `rot`). New items go to the first spot that fits, turned if only that fits.
- Carrying a gun item = owning that weapon. Dropping the last one takes the weapon away; its ammo
  stays with the dropped gun.
- Quick slots 1-3 (under the character; `Config.Inventory.QuickSlots`) hold one item each, any
  size, and count toward the Inventory's weight. Keys 1 / 2 / 3 (gamepad D-pad left / up / right,
  or tapping the quick bar at the bottom of the screen) use the slot: a gun comes out, the same
  key puts it on the back; food / first aid gets used. The default guns
  start in them (the carbine in slot 1). Dropping an item on a full quick slot swaps them.
- Active items shows the gun in your hands. Drag a gun onto it to take it out; drag it out
  (anywhere: onto a slot moves it there too) to put it on your back.
- Dragging the vest out of / onto the Armor slot plays the vest animation (no key: V was removed). A vest taken off
  goes into the inventory with its armor left (on the ground if there's no room). Respawning
  refills the worn vest.
- Dropped items sit in `Workspace.DroppedItems` (attributes Uid / ItemId / Count), show under
  Ground within 8 studs, and can be picked up by dragging or by pressing E. They vanish after 10 min.
  Picking up plays a bend-down-and-grab clip (Tulevo_Pickup, or Tulevo_PickupLeft with a gun in the
  right hand; art/anim/pickup.py, Client/Movement/Moves/Pickup); you can't move or jump while it plays. With E the character walks up to the
  item first and the client asks the server for it when the hand reaches it (0.5 s into the clip);
  the server's prompt handler takes it itself after 5 s if that request never comes.
- The middle box shows a still picture of your own character from the front in the idle pose
  (a copy posed by the idle animation's first frame out of sight, then frozen), with the worn
  vest and a gun on the back (a gun in the hand is left out). Rebuilt when the window opens and
  when the vest, a gun or clothes change while it's open.
- Window size: the 820 x 700 design is scaled to fit the screen. On short screens (phones held
  sideways, where that would be under 0.75x) it fills 86% of the width instead, sits under the
  Roblox top bar, and the Ground/Backpack and middle columns scroll (the inventory grid gets
  shorter and scrolls by itself). Scrolling is frozen while you drag an item.
- Not saved between sessions yet. Equipment slots and the Bag slot are layout only.
