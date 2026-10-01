# Don't Trust The Levels

COMP 4900SEF — Creative Programming for Games · Group Project
**A 2D action deception platformer.** The level lies to you.

- Engine: **Unreal Engine 4.27.2** (2D Side Scroller template, Paper2D)
- Short path (junction): **`C:\dtl`** → this project
- In-engine root: `/Game/DontTrustTheLevels/`
- Design doc: `Docs/Proposal.md` · **Structure standard: `Docs/Structure.md`**

## Opening the project

1. Install Unreal Engine **4.27** (Epic Games Launcher)
2. Double-click `DontTrustTheLevels.uproject`
3. Press **Play**

## Read this first

**[`Docs/Structure.md`](Docs/Structure.md)** is the authoritative reference for
folder layout, naming standard, and ownership rules. Read it before creating or
moving any asset.

## Folder layout

| Path | What | Committed? |
|---|---|---|
| `Content/DontTrustTheLevels/` | **All game assets** (levels, blueprints, sprites, textures) | ✅ LFS |
| `Content/2DSideScroller/` `Content/2DSideScrollerBP/` | UE template — **delete after migration** | ✅ LFS |
| `Assets/PixelAdventure/` | Source PNGs (Pixel Adventure, CC0 by Pixel Frog) | ✅ LFS |
| `Docs/` | Proposal, Structure.md, figures | ✅ |
| `Scripts/` | Python tooling (import, level build, remote exec) | ✅ |
| `Config/` | Engine config (input, maps, plugins) | ✅ |
| `Intermediate/` `Saved/` `DerivedDataCache/` | Generated — **never commit** | ❌ ignored |

## Asset naming

Full standard in `Docs/Structure.md` §3. Quick reference:

| Prefix | Type | Example |
|---|---|---|
| `BP_` | Blueprint | `BP_TrapBase` |
| `BPI_` | Blueprint Interface | `BPI_Killable` |
| `WBP_` | Widget Blueprint (UI) | `WBP_MainMenu` |
| `T_` | Texture | `T_Terrain_D` |
| `SPR_` | PaperSprite | `SPR_Floor` |
| `SPF_` | Sprite frame | `SPF_Player_Run_03` |
| `FLB_` | PaperFlipbook | `FLB_Player_Run` |
| `A_` | Audio | `A_Jump` |
| `L_` | Level / Map | `L_Level_01` |
| `E_` `ST_` `DT_` | Enum / Struct / Data Table | `E_GunEffect` |

Paper2D chain: `T_` → `SPR_` (sliced) → `FLB_` → `BP_`

## Modular ownership (each pillar is independent)

| # | Pillar | Owns | Folder |
|---|---|---|---|
| 1 | Player controller & movement | `BP_Player`, movement, respawn | `Player/` + `Core/` |
| 2 | Trap system | `BP_TrapBase` + children | `Traps/` |
| 3 | Weapons & shooting | `BP_Weapon_*`, projectiles, melee | `Weapons/` |
| 4 | Enemies | `BP_Mimic`, `BP_Sentinel`, `BP_Lurker`, `BP_Chaser` | `Enemies/` |
| 5 | Level design & layout | level maps, difficulty curve | `Levels/` + `Environment/` |
| 6 | UI, audio & progression | menus, HUD, SFX, save | `UI/` + `Audio/` |

**Rule: two people never edit the same asset.** Levels reference Blueprints by
class — a trap fix never breaks a map.

## Python tools

```bat
:: run a script in the live editor (editor must be OPEN)
py -3 Scripts\make_folders.py
py -3 Scripts\import_art.py

:: headless, no editor
Scripts\runpy.bat Scripts\yourscript.py
```

### ⚠️ Remote execution is project-guarded

`Scripts/ue_remote.py` discovers editors by **UDP multicast broadcast** — it finds
*any* UE editor on the machine, regardless of which project is open. An unguarded
script can therefore write foreign asset paths into the wrong project. (This
actually happened: an old-project script rewrote this project's flipbooks with
`/Game/DTF/...` references.)

**Always pass the guard:**

```python
ue.connect(timeout=15, expected_project="DontTrustTheLevels")
```

It refuses to run if the connected editor has a different project open.

## Git workflow

1. `git pull` before you start
2. Work only in **your pillar's folder** (and your own level map)
3. Commit small: one feature per commit, message = what changed
4. `git push` when the editor is **closed** (`.uasset` files lock while open)
5. Never edit someone else's map — ask, or make your own level

## Credits

- Art: [Pixel Adventure 1](https://pixelfrog-assets.itch.io/pixel-adventure-1) by Pixel Frog (CC0)
- Engine: Unreal Engine 4.27, Epic Games
