# Tulevo

Roblox game, synced into Studio with LiveSync (the same setup as JustClips/Dev).

Push to `main` and the change shows up in the open Studio place within a few seconds.

| Folder | Goes to |
|---|---|
| `src/shared` | ReplicatedStorage.Shared |
| `src/server` | ServerScriptService.Server |
| `src/client` | StarterPlayer.StarterPlayerScripts.Client |
| `src/gui` | StarterGui |
| `src/workspace` | Workspace |

File names: `Name.server.luau` = Script, `Name.client.luau` = LocalScript, `Name.luau` = ModuleScript,
a folder with `init.luau` becomes that script. `.model.json` and `.meta.json` work like in Rojo.

## Connect Studio

Open the Tulevo place, open the LiveSync panel, set the repository to `JustClips/tulevo`, branch `main`, press Connect.
The place remembers it. The plugin and server live in JustClips/Dev (`studio-plugin/`, `sync-server/`).
