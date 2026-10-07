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

It also documents the things that cost us the most time to work out:

- **§9 Interfaces** — how systems talk to each other (and why not to cast)
- **§10 Rendering** — pixel-art settings, the vignette trap, pixel-perfect scaling
- **§11 Automation boundary** — what Python can and cannot do

Feature guides: **[`Docs/FakeFloorTrap.md`](Docs/FakeFloorTrap.md)** (paintable
collapsing floor). Camera dead-zone: see the blueprint diagrams in
`Saved/Screenshots/Windows/DeadZoneCamera_Diagrams.html` (local only).

**[`Docs/LfsLocking.md`](Docs/LfsLocking.md)** — **every member must read this
once and do its one-time setup**: UE4 binaries cannot be merged by git, so the
project uses **Git LFS file locking**. Blueprint/map files are read-only until
you lock them; the editor locks a file the moment you edit it; teammates get a
red padlock and are refused. Without this setup, two people editing the same
blueprint silently destroys one person's work.

## Current state

| System | Status |
|---|---|
| Project structure + naming standard | ✅ documented |
| Level 0 (`L_Level_00`) | ✅ floor, collision, background tilemap, fixed camera |
| Player (`BP_Player`) | ✅ Ninja Frog, moves, jumps, flips, animation states |
| Death & respawn | ✅ `BPI_Killable` → instant respawn at level start |
| Trap base (`BP_TrapBase`) | ✅ overlap → interface → kill |
| Trap art | ✅ Spikes, Saw imported |
| Weapons / enemies / UI | ⬜ not started |

## Folder layout

| Path | What | Committed? |
|---|---|---|
| `Content/DontTrustTheLevels/` | **All game assets** (levels, blueprints, sprites, textures) | ✅ LFS |
| `Content/2DSideScroller/` `Content/2DSideScrollerBP/` | UE template — **delete after migration** | ✅ LFS |
| `Assets/PixelAdventure/` | Source PNGs (Pixel Adventure, CC0 by Pixel Frog) | ✅ LFS |
| `Docs/` | Proposal, Structure.md, figures | ✅ |
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

## Python tooling (local-only, not in the repo)

The Python tooling (asset import, level building, live-editor remote
execution) is **not tracked by git** — it lives in `Scripts/` on machines
that already have it, and is gitignored everywhere else. If you need a
script workflow, ask the person who wrote it; do not expect it on a fresh
clone.

Historical note for whoever rebuilds it: the bridge client was
`Scripts/ue_remote.py` (UDP multicast 239.0.0.1:6766, `ue_py` protocol,
editor dials back into a local TCP server on 6776). It discovers *any*
UE editor on the machine — an unguarded script can write foreign asset
paths into the wrong project (this actually happened once). Anyone
rebuilding it must keep the project guard:

```python
ue.connect(timeout=15, expected_project="DontTrustTheLevels")
```

## Git workflow

1. **Connect Source Control first** (Git + ✓ Use Git LFS Locking) — see
   [`Docs/LfsLocking.md`](Docs/LfsLocking.md). Editing without a lock is how
   blueprints get destroyed.
2. `git pull` before you start (editor **closed**)
3. Work only in **your pillar's folder** (and your own level map)
4. Commit small: one feature per commit, message = what changed
5. `git push` when the editor is **closed** — pushing **releases your locks**,
   so teammates can edit what you finished
6. Never edit someone else's map — ask, or make your own level

## Credits

- Art: [Pixel Adventure 1](https://pixelfrog-assets.itch.io/pixel-adventure-1) by Pixel Frog (CC0)
- Engine: Unreal Engine 4.27, Epic Games
