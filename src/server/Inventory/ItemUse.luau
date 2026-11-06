--[[
	What each server use action does (Shared/Items/Actions.luau lists them; an item picks one
	with Use = { Action = ..., Amount = ..., Time = ... }). InventoryService runs the timer,
	checks the item is still carried and takes one of it; these only decide and apply.

	Each action:
	  can(ctx)   -> ok, reason?  optional: asked before starting and again at the end
	  apply(ctx)                 does it
	ctx = { player, character, humanoid, def (Shared/Items ItemDef), use (def.Use) }
]]

export type Ctx = {
	player: Player,
	character: Model,
	humanoid: Humanoid,
	def: any,
	use: any,
}
export type Handler = {
	can: ((ctx: Ctx) -> (boolean, string?))?,
	apply: (ctx: Ctx) -> (),
}

local function heal(ctx: Ctx)
	local h = ctx.humanoid
	h.Health = math.min(h.MaxHealth, h.Health + (ctx.use.Amount or 0))
end

local ItemUse: { [string]: Handler } = {
	Heal = {
		can = function(ctx)
			if ctx.humanoid.Health >= ctx.humanoid.MaxHealth then
				return false, "Already at full health"
			end
			return true
		end,
		apply = heal,
	},
	Drink = {
		apply = heal,
	},
}

return ItemUse
