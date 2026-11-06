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
