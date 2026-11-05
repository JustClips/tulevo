-- Starts the inventory (Server/Inventory/InventoryService): item models for icons and the
-- ground, everyone's starting kit, the move / drop / pick up remotes.
local InventoryService = require(script.Parent:WaitForChild("Inventory"):WaitForChild("InventoryService"))

InventoryService.start()
