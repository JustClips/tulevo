# Inventory

N opens the window (phone: Bag button). Roblox's default backpack bar is off.

| Where | What |
|---|---|
| `src/shared/Items/init.luau` | Item registry: name, kind, **Weight (kg)**, **Cells (size in the grid, wide x tall)**, stack size, model, icon view. Weapons and the vest are items too |
| `src/shared/Items/Grid.luau` | Placing maths shared by server and client: footprints, overlaps, first free spot |
| `src/shared/Weapons/Defs/*.luau` | Each weapon's `Weight` and `Cells` (carbine 4 x 2) |
| `src/shared/Armor/init.luau` | Each armor's `Weight` and `Cells` (vest 2 x 2) |
| `Config.Inventory` | Grid sizes (Inventory 5 x 14, Backpack 4 x 4) and weight limits (30 kg, 10 kg), starting items, ground / pickup range, dropped item lifetime |
| `src/server/Inventory/InventoryService.luau` | Server-owned inventories, move / stack / swap with weight checks, drop to the ground, pick up, the Armor slot |
| `src/server/Inventory/ItemModels.luau` | Loads every item's model into `ReplicatedStorage.ItemModels` (inventory icons, dropped items) |
| `src/client/Inventory.client.luau` | The window: layout, 3D item icons, drag and drop, hover info, Ground list |
| `art/icons/` | ForgeGUI UI icons (`gen.py` -> `raw/`, `proc.py` -> white `out/`), uploaded by `tools/upload_icons.py` into `Shared/IconIds` |

Everyone starts with the Carbine Rifle (`Config.Weapons.DefaultLoadout`), a mead, a chaser and a
first-aid kit in the inventory, and the armor vest worn (Armor slot).

- Items cover several cells and sit at their top-left cell. While dragging, a green box shows
  where the item lands (red = overlaps, out of the grid or too heavy) and R turns it 90 degrees
  (stored as `rot`). New items go to the first spot that fits, turned if only that fits.
- Carrying a gun item = owning that weapon (5 / Q still draw it). Dropping the last one takes the
  weapon away; its ammo stays with the dropped gun.
- V, or dragging the vest out of / onto the Armor slot, plays the vest animation. A vest taken off
  goes into the inventory with its armor left (on the ground if there's no room). Respawning
  refills the worn vest.
- Dropped items sit in `Workspace.DroppedItems` (attributes Uid / ItemId / Count), show under
  Ground within 8 studs, and can be picked up by dragging or by holding E. They vanish after 10 min.
- Not saved between sessions yet. Equipment slots, the Bag slot and quick slots 1-3 are layout only.
