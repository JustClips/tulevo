-- Buildings of the tulevo city, placed by Server/CityBuildings.server.luau.
-- Each one is a Blender model (art/blender/...) uploaded with tools/upload_models.py;
-- Model = its key in Shared.ModelIds. Ground, roads and the spawn are in
-- src/workspace/City.model.json (tools/build_city_map.py).
--
--   At        where the model's origin (ground centre in Blender) goes, in studs
--   Yaw       turn in degrees (0 = Blender front faces -Z, north on the map)
--   BoxCenter the model's bounding-box centre relative to its origin, Roblox axes
--             (from the Blender meta.json: X = -x, Y = z, Z = y). Imports don't keep
--             the Blender origin, so this is how the model lands in the right spot.
--   Scale     model scale (1 = built in studs)
return {
	{
		Name = "ArkwellBank",
		Model = "BankTower",
		At = Vector3.new(0, 0.6, 0),
		Yaw = 0,
		BoxCenter = Vector3.new(0, 350.56, -10),
		Scale = 1,
	},
}
