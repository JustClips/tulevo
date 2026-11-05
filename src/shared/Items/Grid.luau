--[[
	Inventory grid maths, shared by the server (Server/Inventory) and the window
	(Client/Inventory) so both agree on where things fit.

	A container is cols x rows cells, numbered row by row from 1 (slot = row * cols + col + 1,
	0-based col/row). An item sits at its top-left slot and covers W x H cells (its def's
	Cells, default 1 x 1); a turned item (rot = true) covers H x W.

		Grid.size(item)                          -> w, h  (after turning)
		Grid.occupancy(list, cols)               -> { [cell slot] = top-left slot of the item there }
		Grid.fits(list, cols, rows, slot, w, h, ignoreSlot?) -> boolean
		Grid.findSpot(list, cols, rows, w, h)    -> slot?
	list is { [top-left slot] = item } (anything with .id and .rot).
]]

local Items = require(script.Parent)

local Grid = {}

function Grid.baseSize(id: string): (number, number)
	local def = Items.get(id)
	local c = def and def.Cells
	if c then
		return math.max(1, c.X), math.max(1, c.Y)
	end
	return 1, 1
end

function Grid.size(item: any): (number, number)
	local w, h = Grid.baseSize(item.id)
	if item.rot then
		return h, w
	end
	return w, h
end

function Grid.pos(slot: number, cols: number): (number, number)
	return (slot - 1) % cols, (slot - 1) // cols
end

function Grid.slot(col: number, row: number, cols: number): number
	return row * cols + col + 1
end

function Grid.occupancy(list: { [number]: any }, cols: number): { [number]: number }
	local occ = {}
	for anchor, item in list do
		local w, h = Grid.size(item)
		local c0, r0 = Grid.pos(anchor, cols)
		for r = r0, r0 + h - 1 do
			for c = c0, c0 + w - 1 do
				occ[Grid.slot(c, r, cols)] = anchor
			end
		end
	end
	return occ
end

-- Does a w x h item fit with its top-left at slot? ignoreSlot: an item that doesn't count
-- (the one being moved, still sitting in its old spot).
function Grid.fits(
	list: { [number]: any },
	cols: number,
	rows: number,
	slot: number,
	w: number,
	h: number,
	ignoreSlot: number?,
	occ: { [number]: number }?
): boolean
	if slot < 1 or slot % 1 ~= 0 then
		return false
	end
	local c0, r0 = Grid.pos(slot, cols)
	if c0 + w > cols or r0 + h > rows then
		return false
	end
	occ = occ or Grid.occupancy(list, cols)
	for r = r0, r0 + h - 1 do
		for c = c0, c0 + w - 1 do
			local o = (occ :: any)[Grid.slot(c, r, cols)]
			if o and o ~= ignoreSlot then
				return false
			end
		end
	end
	return true
end

-- First top-left slot (row by row) where a w x h item fits.
function Grid.findSpot(list: { [number]: any }, cols: number, rows: number, w: number, h: number): number?
	local occ = Grid.occupancy(list, cols)
	for slot = 1, cols * rows do
		if not occ[slot] and Grid.fits(list, cols, rows, slot, w, h, nil, occ) then
			return slot
		end
	end
	return nil
end

return Grid
