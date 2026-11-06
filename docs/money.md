# Money and clock HUD

| Where | What |
| --- | --- |
| `src/server/Money.luau` | Cash + Bank per player (Player attributes `Cash` / `Bank`), add/deposit/withdraw API, DataStore save |
| `src/server/MoneyRunner.server.luau` | starts Money |
| `src/shared/GameTime.luau` | in-game time/date/weekday, same on server and client |
| `src/server/GameClock.server.luau` | starts the clock, turns `Lighting.ClockTime` |
| `src/client/InfoHud.client.luau` | panel right of the radar: time, date, weekday, cash, bank, +$/-$ pop |
| `Config.Money`, `Config.Time` | start balances, saving, day length (48 real min), start hour |

Giving money from server code:

```lua
local Money = require(game.ServerScriptService.Server.Money)
Money.addCash(player, 250)   -- false if it would go below 0
Money.deposit(player, 100)   -- wallet -> bank
```
