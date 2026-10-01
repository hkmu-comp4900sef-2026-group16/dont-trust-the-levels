# Structure.md — Don't Trust The Levels

The asset-folder structure, naming standard, and ownership rules for this project.
**Read this before creating or moving any asset.**

- Engine: Unreal Engine **4.27.2** (2D Side Scroller template, Paper2D)
- Project root: `...\Projects\DontTrustTheLevels\`
- Short path (junction): **`C:\dtl`** → the long path above
- In-engine root: `/Game/DontTrustTheLevels/`

---

## 1. Why this structure

**We organise by pillar (who owns it), not by asset type (what it is).**

The previous project mixed both taxonomies: top-level folders were a mixture of asset
*types* (`Background/`, `Characters/`, `Traps/`) and asset *classes* (`Blueprints/`,
`Maps/`). The consequence was that one feature lived in two unrelated places — a trap's
art in `Traps/`, its logic in `Blueprints/Traps/` — so no single person owned a trap.

With six people each owning a technical pillar, **one pillar = one folder** is the only
layout where "two people never edit the same asset" is enforceable.

Corollary: each pillar folder holds **art and logic together** (`Blueprints/`,
`Sprites/`, `Textures/`, `Animations/` as needed).

---

## 2. Folder tree

```
Content/
├── 2DSideScroller/              } UE template art
├── 2DSideScrollerBP/            } UE template blueprints + example map
│                                }   -> DELETE after migration (see §6)
│
└── DontTrustTheLevels/          <- OUR GAME
    ├── Core/                    shared: GameMode, PlayerController, interfaces, data
    │   ├── Blueprints/
    │   ├── Interfaces/          BPI_*
    │   └── Data/                E_* ST_* DT_*
    ├── Player/
    │   ├── Blueprints/          BP_Player
    │   ├── Sprites/             SPR_Player_*
    │   │   └── Frames/          SPF_Player_*
    │   ├── Animations/          FLB_Player_*
    │   └── Textures/            T_Player_*_D
    ├── Traps/
    │   ├── Blueprints/          BP_TrapBase + children
    │   ├── Sprites/
    │   └── Textures/
    ├── Weapons/
    │   ├── Blueprints/          BP_Weapon_Pistol, BP_Weapon_Blade, BP_Projectile
    │   ├── Sprites/
    │   └── Textures/
    ├── Enemies/
    │   ├── Blueprints/          BP_Mimic, BP_Sentinel, BP_Lurker, BP_Chaser
    │   ├── Sprites/
    │   │   └── Frames/
    │   ├── Animations/
    │   └── Textures/
    ├── Environment/             terrain, background, toxic platforms
    │   ├── Sprites/
    │   ├── Textures/
    │   └── Materials/
    ├── Levels/                  L_Level_01 ... L_Level_05
    ├── UI/                      WBP_*
    └── Audio/                   A_*
```

**Note:** `Content/` on disk **is** `/Game/` in engine and in code.
`Content\DontTrustTheLevels\Player\Sprites\SPR_Player.uasset`
== `/Game/DontTrustTheLevels/Player/Sprites/SPR_Player`.

---

## 3. Naming standard

General rules (from the unit standard):
- English names only — no spaces, diacritics, or special symbols
- **PascalCase** for asset and folder names
- Underscores `_` separate prefix, base name, and suffixes
- **Two-digit** numbers for variants (`01`, `02`)

### Prefixes

| Prefix | Type | Example |
|---|---|---|
| `BP_` | Blueprint | `BP_TrapBase` |
| `BPI_` | Blueprint Interface | `BPI_Killable` |
| `E_` | Enum | `E_GunEffect` |
| `ST_` | Struct | `ST_TrapConfig` |
| `DT_` | Data Table | `DT_GunEffects` |
| `WBP_` | Widget Blueprint (UI) | `WBP_MainMenu` |
| `T_` | Texture | `T_Terrain_D` |
| `M_` / `MI_` | Material / Material Instance | `MI_Wood_Dark` |
| `SPR_` | PaperSprite | `SPR_Floor` |
| `SPF_` | Sprite frame (single anim frame) | `SPF_Player_Run_03` |
| `FLB_` | PaperFlipbook | `FLB_Player_Run` |
| `A_` | Audio (Sound Wave / Cue) | `A_Jump` |
| `L_` | Level / Map | `L_Level_01` |
| `FXS_` | Niagara System | `FXS_Explosion` |
| `SM_` / `SK_` | Static / Skeletal Mesh | *(unused — 2D game)* |

### Texture suffixes

Trailing suffix denotes the texture's map type:

| Suffix | Meaning |
|---|---|
| `_D` | Diffuse / Base Color |
| `_N` | Normal Map |
| `_M` / `_R` | Roughness |
| `_AO` | Ambient Occlusion |
| `_E` | Emissive |

All textures in this project are base-colour, so **every texture carries `_D`**.

### Why `SPR_` / `SPF_` / `FLB_`

The unit standard reserves **`S_` for Sound Waves**. Our old convention used `S_` for
**PaperSprite** — a direct collision (`S_Floor` reads as an audio file). The standard
defines no Paper2D prefixes at all, so we extend it: `SPR_`/`SPF_`/`FLB_`. This frees
`S_` for audio and makes sprite assets unambiguous.

### The Paper2D chain

Every animated thing follows the same pipeline:

```
T_  (texture)  ->  SPR_ (sprite, sliced)  ->  FLB_ (flipbook)  ->  BP_ (logic)
                    SPF_ = individual frames feeding a flipbook
```

---

## 4. Ownership (one pillar = one folder)

| # | Pillar | Owns | Folder |
|---|---|---|---|
| 1 | Player controller & movement | `BP_Player`, movement, respawn | `Player/` + `Core/` |
| 2 | Trap system | `BP_TrapBase` + children | `Traps/` |
| 3 | Weapons & shooting | `BP_Weapon_*`, projectiles, melee | `Weapons/` |
| 4 | Enemies | `BP_Mimic`, `BP_Sentinel`, `BP_Lurker`, `BP_Chaser` | `Enemies/` |
| 5 | Level design & layout | level maps, difficulty curve | `Levels/` + `Environment/` |
| 6 | UI, audio & progression | menus, HUD, SFX, save | `UI/` + `Audio/` |

**Rules:**
1. **Never two people in the same asset.** One `.uasset`/`.umap` has exactly one owner.
2. Work only in **your pillar's folder** (and your own level map).
3. Levels reference Blueprints **by class** — a trap fix never breaks a map.
4. `Core/` is shared: changes need the owner's agreement (pillar 1).
5. Commit with the **editor closed** — `.uasset` files lock while open.

---

## 5. Old project -> new naming map

Reference for the migration from `DontTrustTheFloor`.

| Old (DTF) | New (DTL) | Folder |
|---|---|---|
| `T_Terrain` | `T_Terrain_D` | `Environment/Textures` |
| `S_Floor`, `S_Dirt` | `SPR_Floor`, `SPR_Dirt` | `Environment/Sprites` |
| `S_Background` | `SPR_Background` | `Environment/Sprites` |
| `T_Background_Blue` | `T_Background_Blue_D` | `Environment/Textures` |
| `S_Saw`, `S_Spikes` | `SPR_Saw`, `SPR_Spikes` | `Traps/Sprites` |
| `T_Saw`, `T_Spikes`, `T_SpikedBall` | `T_Saw_D`, `T_Spikes_D`, `T_SpikedBall_D` | `Traps/Textures` |
| `S_Start`, `S_EndDoor` | `SPR_Start`, `SPR_EndDoor` | `Environment/Sprites` |
| `T_StartIdle`, `T_EndIdle`, `T_EndPressed` | `T_StartIdle_D`, `T_EndIdle_D`, `T_EndPressed_D` | `Environment/Textures` |
| `SP_PinkMan_Idle_00..10` | `SPF_Player_Idle_00..10` | `Player/Sprites/Frames` |
| `SP_PinkMan_Run_00..11` | `SPF_Player_Run_00..11` | `Player/Sprites/Frames` |
| `SP_PinkMan_Fall_00`, `_Jump_00` | `SPF_Player_Fall_00`, `_Jump_00` | `Player/Sprites/Frames` |
| `FB_PinkMan_*` | `FLB_Player_*` | `Player/Animations` |
| `T_PinkMan_*` | `T_Player_*_D` | `Player/Textures` |
| `BP_PinkMan` | `BP_Player` | `Player/Blueprints` |
| `BP_TrapBase` | `BP_TrapBase` *(unchanged)* | `Traps/Blueprints` |
| `Room_000` (old project) | `L_Level_01` | `Levels` |

`SPF_Player_Run_00..11` already satisfies the two-digit rule — no renumbering needed.

---

## 6. Template migration (do this later, deliberately)

The UE **2D Side Scroller** template ships working input bindings, a Paper2D character,
and a side-scroller camera. We keep it while building, then migrate:

1. Copy `2DSideScrollerGameMode` logic into `Core/Blueprints/BP_GameMode`
2. Create `Player/Blueprints/BP_Player` (see §7)
3. Point `Config/DefaultEngine.ini` at `BP_GameMode` and `L_Level_01`
4. Build `L_Level_01` in `Levels/`
5. **Then** delete `Content/2DSideScroller/` and `Content/2DSideScrollerBP/`

Do not delete the template folders early — the character and GameMode are still in use.

---

## 7. Open decisions

- **`BP_Player` inheritance:** from the template's `2DSideScrollerCharacter` (free
  movement, but carries template baggage) or from `PaperCharacter` directly (cleaner,
  movement rebuilt). **Recommendation:** inherit from the template character for now,
  migrate to `PaperCharacter` once movement is tuned.
- **`Environment/` owner:** assigned to pillar 5 (level design) — it has no dedicated
  pillar in the work-allocation table.

---

## 8. Practical notes

- **Empty folders do not survive git.** Add a `.gitkeep` to any folder that must exist
  before it has assets.
- **Junction:** `C:\dtl` → project root. Use it in scripts and shell commands to keep
  paths short (Windows `MAX_PATH` is 260; the long path already costs 144).
- **Remote-execution guard:** `Scripts/ue_remote.py` refuses to run unless the connected
  editor has **this** project open. Multicast discovery finds *any* editor on the machine,
  so an unguarded script can write foreign asset paths into the wrong project. Always
  pass `expected_project="DontTrustTheLevels"`.
