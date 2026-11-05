-- GPS: one waypoint and the route to it along the roads.
-- Nav.set(position) / Nav.clear(). Nav.Changed fires when the waypoint or the
-- route changes; read Nav.waypoint (Vector3?) and Nav.route ({ Vector3 }).
-- The route follows the player and the waypoint clears on arrival.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local MapData = require(script.Parent:WaitForChild("MapData"))

local ARRIVE = 18 -- studs from the waypoint that count as arrived
local REROUTE_MOVE = 4 -- studs the player moves before the route is redone

local player = Players.LocalPlayer

local Nav = {}
Nav.waypoint = nil :: Vector3?
Nav.route = {} :: { Vector3 }

local changed = Instance.new("BindableEvent")
Nav.Changed = changed.Event

local lastFrom: Vector3? = nil

local function playerPos(): Vector3?
	local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
	return root and (root :: BasePart).Position
end

local function recompute(force: boolean?)
	local wp = Nav.waypoint
	local pos = playerPos()
	if not wp or not pos then
		return
	end
	local flatPos = Vector3.new(pos.X, 0, pos.Z)
	if (flatPos - Vector3.new(wp.X, 0, wp.Z)).Magnitude <= ARRIVE then
		Nav.clear()
		return
	end
	if not force and lastFrom and (flatPos - lastFrom).Magnitude < REROUTE_MOVE then
		return
	end
	lastFrom = flatPos
	Nav.route = MapData.route(flatPos, wp)
	changed:Fire()
end

function Nav.set(position: Vector3)
	Nav.waypoint = Vector3.new(position.X, 0, position.Z)
	Nav.route = {}
	lastFrom = nil
	changed:Fire()
	recompute(true)
end

function Nav.clear()
	if Nav.waypoint == nil then
		return
	end
	Nav.waypoint = nil
	Nav.route = {}
	lastFrom = nil
	changed:Fire()
end

MapData.Changed:Connect(function()
	recompute(true)
end)

local acc = 0
RunService.Heartbeat:Connect(function(dt)
	acc += dt
	if acc >= 0.25 then
		acc = 0
		recompute(false)
	end
end)

return Nav
