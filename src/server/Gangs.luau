--[[
	Gangs as Teams (Config.Gangs) + a Civilians team for everyone else.
	A player's gang is player.Team; the Team's "Gang" attribute holds the gang Id, which
	matches the Gang attribute on that gang's SpawnLocation in the city.
	Gangs.set(player, id | nil) moves a player to a gang (nil = Civilians).
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Teams = game:GetService("Teams")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))

local Gangs = {}

local teams: { [string]: Team } = {}

local function makeTeam(name: string, color: Color3, gang: string?): Team
	local team = Teams:FindFirstChild(name) :: Team?
	if not team then
		local t = Instance.new("Team")
		t.Name = name
		t.Parent = Teams
		team = t
	end
	local t = team :: Team
	t.TeamColor = BrickColor.new(color)
	t.AutoAssignable = gang == nil
	t:SetAttribute("Gang", gang)
	return t
end

local civilians = makeTeam("Civilians", Color3.fromRGB(242, 243, 243), nil)
for _, g in Config.Gangs do
	teams[g.Id] = makeTeam(g.Name, g.Color, g.Id)
end

function Gangs.get(player: Player): string?
	local team = player.Team
	return team and team:GetAttribute("Gang") :: string?
end

function Gangs.set(player: Player, id: string?): boolean
	if id ~= nil and not teams[id] then
		return false
	end
	player.Team = if id then teams[id] else civilians
	return true
end

Players.PlayerAdded:Connect(function(player)
	if not player.Team then
		player.Team = civilians
	end
end)
for _, p in Players:GetPlayers() do
	if not p.Team then
		p.Team = civilians
	end
end

return Gangs
