-- Starts the weapon system (Server.Weapons). Starting weapons (Config.Weapons.DefaultLoadout,
-- plus StudioLoadout in Studio play tests) are now inventory items: Server/Inventory puts them
-- in everyone's inventory and gives the weapon while the item is carried.
require(script.Parent:WaitForChild("Weapons"):WaitForChild("WeaponService"))
