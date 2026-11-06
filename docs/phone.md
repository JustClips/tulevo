# Phone

The in-game phone (modern iPhone-style, with a Dynamic Island). Only the layout and the
open/close animation exist so far; apps are placeholders.

## Controls
- **Up arrow** opens / closes it (on foot; in a car the arrows still drive and the phone is put away).
- **D-pad down** on a gamepad (D-pad up/left/right are quick slots).
- Phones/tablets: the small phone button on the right edge.
- **Backspace** / **B**: back (app -> home -> phone closed). The home bar at the bottom of the
  screen goes home, the side (power) button closes it.

It slides up from under the bottom-right corner GTA-style (`Config.Phone.OpenTime`), the
screen wakes from black, and it drops back down on close. Knocked down = phone closes.

## Files (src/client)
- `PhoneRunner.client.luau` starts it.
- `Phone/init.luau` controller + API: `open/close/toggle/isOpen`, `openApp(id)`, `home()`,
  `notify(text, seconds)` (grows the Dynamic Island), `Opened`/`Closed` events.
- `Phone/Frame.luau` builds the body, side buttons, screen, status bar (in-game clock),
  Dynamic Island, home bar. `Phone/Theme.luau` sizes/colours (phone units: 300 wide).
- `Phone/Home.luau` home screen grid (4 across) + dock. `Phone/Island.luau` island animation.
- `Phone/PhoneArt.luau` (generated) ForgeGUI body picture + screen hole + wallpaper ids.
  Without a body picture the body is drawn from Frames.
- `Phone/AppIcons.luau` (generated) app icon glyph pictures by app Id.
- `Phone/Apps/` one module per app. `Placeholders.luau` holds the empty ones.

## Adding an app
Make `Phone/Apps/MyApp.luau`:

```lua
return {
	Id = "Bank", Name = "Bank", Color = Color3.fromRGB(28, 120, 80), Order = 12,
	Icon = require(script.Parent.Parent.AppIcons).Bank, -- or nil = first letter
	open = function(page, phone) -- page = full-screen TextButton (blocks taps to the home screen) under the status bar, title already there
	end,
	close = function(page) end, -- optional
}
```

and remove its line from `Placeholders.luau`. Pages slide in from the right.

## Art (art/phone)
- `gen.py` ForgeGUI body (`mixed`, transparent) + wallpaper (`thumbnail`) through the key pool
  (JustClips/Dev tools/forgegui.py). `gen_apps.py` app glyphs (`gui_icon`).
- `proc.py` cuts the screen hole, crops the wallpaper to portrait, makes white glyph masks.
- `python3 tools/upload_icons.py --set phone` and `--set phone_apps` upload and write the Luau ids.
