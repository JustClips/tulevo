# Human (realistic test NPC)

Original static posed human for tulevo, built from **CC0 MakeHuman assets** (base mesh hm08, macro/detail
targets, default rig + weights, young skin textures, casual suit 06, shoes 05, short02 hair, brows, eyes).
Not based on any game character.

- `prep_textures.py <assets_out> <makehuman_system_assets>`: plain white tee (MakeHuman logo/url removed),
  grey shoe accents, hair texels filled so the hair still looks right when drawn opaque.
- `build_human.py -- <data> <out> [--samples N] [--no-render]`: shapes the body with targets, fits the
  clothes/hair/eyes (mhclo), cuts hidden skin, poses the default rig (arms down), paints stubble, brows and
  hairline into the skin, splits Head/Arms with their own 1024 maps, exports `Human.glb` in studs (6.2 tall).

Data bundle (28 MB, not in git): project files `tulevo-human/human_bundle_v1.zip`. Sources:
files.makehumancommunity.org (makehuman_system_assets_cc0.zip) and the mpfb2 repo `src/mpfb/data`.

## v5: Microsoft Rocketbox base (current)

`build_rocketbox.py -- <avatar_dir> <out> [--samples N]` converts a Microsoft Rocketbox avatar
(github.com/microsoft/Microsoft-Rocketbox, **MIT licence**, artist-made realistic humans with 2048 colour +
normal maps) to tulevo: GTA-style idle pose on the Bip01 rig, mouth closed, one subdivision level, Body split
into BodyUpper/BodyLower (<20k tris each), 1024 colour + normal maps, pocket stitch designs patched out
(`CLEAN` regions), GLB in studs. Current guy: Male_Adult_12 (denim jacket, white tee, jeans, white sneakers).
Bundle: project files `tulevo-human/rocketbox_m12_v1.zip`. Check every map at full size for text/logos first.
