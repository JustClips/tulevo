-- Roblox Model asset ids for the "City Prop" street lamps and traffic signals
-- (already uploaded in Roblox, no GLB in art/models). Load one with
-- InsertService:LoadAsset(CityPropIds.StreetLight1).
--
-- Keys are PascalCase of the Roblox marketplace name so the shape in code
-- matches what's in Studio.
--
-- The lamps are placed on the street light spots by Server/CityPropPlacer (which lamp goes on
-- which street is set there). The signals are not placed yet: the old signal masts are still
-- part of the StreetCorners mesh and need a Blender re-bake first.
return {
	-- Street lamps (24)
	FancyStreetLight1 = 97754943913314,
	FancyStreetLight2 = 98570207290490,
	FancyStreetLight3 = 87444445368872,
	GlobeStreetLight1 = 105090149673945,
	GlobeStreetLight2 = 119185785409084,
	LanternStreetLight = 128136657181236,
	LanternStreetLightColumn = 133217178605463,
	LanternStreetLightDouble = 108922514886354,
	ModernDomeLight = 116680203596441,
	ModernPathLight1 = 82186266076135,
	ModernPathLight2 = 128666822609478,
	ModernStreetLightCones = 96344048869400,
	ModernStreetLightTwin = 94839226070818,
	ModernStreetLightV = 111280756250242,
	ParkingLotLightDouble = 116071764003698,
	ParkingLotLightShort = 121962860709739,
	ParkingLotLightTall = 108082315935826,
	StreetLight1 = 78865298128852,
	StreetLight2 = 113182288171470,
	StreetLight3 = 132193682162313,
	StreetLightDouble1 = 140154547080798,
	StreetLightDouble2 = 99413522164373,
	StreetLightLongArm1 = 136069185718884,
	StreetLightLongArm2 = 118726279309343,

	-- Traffic signals (6)
	CrosswalkSignal = 85146007135172,
	HangingTrafficLight4Way = 90929615384614,
	IntersectionTrafficLight1 = 81383953064972,
	IntersectionTrafficLight2Long = 128462696461043,
	IntersectionTrafficLight3LongDouble = 81675694493474,
	TrafficLightPole = 124315449425935,
}
