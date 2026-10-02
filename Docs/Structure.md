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
    │   ├── Sprites/             SPR_*  (single-frame)
    │   │   └── Frames/          SPF_*  (animation frames)
    │   ├── Animations/          FLB_*
    │   └── Textures/            T_*_D
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
    │   ├── TileSets/            TS_*  (background tilemap)
    │   ├── TileMaps/            TM_*  (background tilemap)
    │   └── Materials/
    ├── Levels/                  L_Level_00 (baseline) ... L_Level_05
    ├── UI/                      WBP_*
    └── Audio/                   A_*
```

**Note:** `Content/` on disk **is** `/Game/` in engine and in code.
`Content\DontTrustTheLevels\Player\Sprites\SPR_Player.uasset`
== `/Game/DontTrustTheLevels/Player/Sprites/SPR_Player`.

---

## 2a. Tilemap vs actors (decided)

**Only the background uses a tilemap. Everything else is actors.**

| Layer | Technique | Why |
|---|---|---|
| **Background** | **Tilemap** (`PaperTileMap`) | Pure decoration — no collision, no logic, ever. One component replaces ~86 sprite actors. |
| Floor | Actors (`PaperSpriteActor`) | Needs collision certainty; trap actors must align exactly with floor tiles. |
| Walls | `BlockingVolume` | Proven pattern; simplest reliable collision. |
| Traps | Actors (`BP_TrapBase` + children) | **Required** — see below. |
| Items / doors | Actors | Per-object state and triggers. |

### Why traps cannot be tilemap tiles

A tilemap is **one component** holding a grid of tile *indices* — the tiles are not
actors. There is therefore nothing to attach logic to: no per-tile overlap event, no
per-tile timer, no per-tile state.

Level Devil's core mechanic is **per-tile betrayal**:

- *this* tile collapses when stepped on → per-tile overlap + timer
- *this* tile is fake → per-tile collision toggle
- spikes erupt from *this* tile → per-tile animation + trigger
- everything resets on death → per-tile state reset

Doing this with a tilemap means a manager that converts world position → tile
coordinates → looks up a side-table of trap tiles. That is fighting the engine, and it
is especially bad here because the project is **Blueprint-only** (no Windows SDK → no
C++), where a per-tile manager is painful to write and maintain.

By contrast one `BP_TrapBase` covers all 15 trap types via parameters — actor-shaped,
which is what the design already is.

**Conclusion:** tilemap for the background only. Revisit the floor *only* if tilemap
collision is empirically proven to work AND a per-tile manager becomes necessary.

### Tilemap setup — the exact numbers (verified working)

Getting a tilemap to line up with the 100uu grid requires **three** values to agree.
Getting any one wrong gives tiles that are the wrong size.

| Setting | Value | Why |
|---|---|---|
| TileSet **tile_size** | **16 × 16** | the tile's size in *pixels* in the atlas |
| TileMap **tile_width / tile_height** | **16 × 16** | must match the tileset's pixel size |
| TileMapComponent **scale** | **6.25** | 16 px × 6.25 = **100 uu** |
| TileMapActor **scale** | **1** | ⚠️ actor scale *multiplies* component scale |

**The two traps:**

1. **Setting `tile_width = 100` looks like the fix but is wrong.** It changes the
   *cell* size to 100uu while the tile *art* still renders at 1 px = 1 uu. Result:
   large empty cells containing tiny tiles. Keep it at 16 and scale instead.

2. **Actor scale and component scale multiply.** Setting both to 6.25 gives
   6.25 × 6.25 = 39× too big. Set the **actor** scale to 1 and the **component**
   scale to 6.25.

**Tile index formula** — the terrain atlas is 22 columns wide:

```
packed_tile_index = row * 22 + col
```

e.g. the grass tile at atlas `(col 6, row 0)` = `0 * 22 + 6` = index **6**.

**Painting from Python:**

```python
info = unreal.PaperTileInfo()
info.set_editor_property("tile_set", tileset)
info.set_editor_property("packed_tile_index", 6)
comp.set_tile(x, y, layer, info)
comp.rebuild_collision()
```

### Tilemap collision — NOT available from Python

Verified empirically: painted tiles + `set_layer_collision(0, True)` +
`rebuild_collision()` produce **no collision geometry**. Line traces pass straight
through.

Collision lives in the tileset's **per-tile data**, which is empty by default and
must be authored **by hand** in the Tile Set Editor → **Collision** tab. Python
cannot create it: `SpriteGeometryShape.shape_type` is **read-only**.

This is why the background is the only tilemap layer — it needs no collision.
If tilemap collision is ever wanted for the floor, budget ~10 minutes of manual
box-drawing per tileset.

**Conclusion:** tilemap for the background only. Revisit the floor *only* if tilemap
collision is empirically proven to work AND a per-tile manager becomes necessary.

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
| `TS_` | PaperTileSet | `TS_Terrain` |
| `TM_` | PaperTileMap | `TM_Background` |
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

- **`Environment/` owner:** assigned to pillar 5 (level design) — it has no dedicated
  pillar in the work-allocation table.

**Resolved:** `BP_Player` inherits from **`PaperCharacter`** directly (not the template
character). The template is to be deleted, so nothing may depend on it.

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

---

## 9. Interfaces — how systems talk to each other

**Rule: systems communicate through Blueprint Interfaces, not direct casts.**

```
BPI_Killable    "I can be killed"      → BP_Player implements it
BPI_Resettable  "I can be reset"       → traps implement it (planned)
BPI_Fireable    "I can be fired"       → weapons implement it (planned)
BPI_NoiseSource "I make noise"         → weapons implement it (planned)
```

**Why not `Cast To BP_Player`?** A cast hard-codes the class name. The player class has
already been renamed once (Pink Man → Ninja Frog); a cast would have broken every trap.
An interface asks *"can you be killed?"* instead of *"are you this specific class?"*.

### Creating an interface

1. Content Browser → `Core/Interfaces/` → **Blueprint Interface** → `BPI_Killable`
2. **My Blueprint → Functions → +** → name it `Kill`
3. **Compile + Save**

⚠️ **Do this BEFORE adding the interface to any class.** If a class adds an interface
while it has no functions, the class does not retroactively pick up functions added
later. Fix: remove and re-add the interface to that class.

### Implementing an interface function

⚠️ **The rule that catches everyone:**

| Interface function has… | Implemented as |
|---|---|
| **No outputs** (void) | **Implement Event** → an event node in the Event Graph |
| **Has outputs** | **Implement Function** → its own graph |

`Kill` has no outputs, so it is an **event**. Looking for "Implement Function" will
never appear — that is expected, not a bug.

### Calling an interface function

**Always drag off an object pin first**, then search the function name:

```
Other Actor ──> Kill (Message)
```

The **(Message)** variant is the correct one. A plain `Kill` node will fail with
*"not marked as callable"*.

⚠️ **Message nodes need a Target.** Dragging off `Other Actor` auto-wires it; creating
the node from empty space leaves Target blank and the compile fails with
*"must have a valid target"*.

### The guard pattern

```
Overlap ─Exec─> Branch ─True─> Kill (Message)
                  ↑                 ↑
     Does Implement Interface ─────┘
     (Other Actor, BPI_Killable)          (Other Actor)
```

`Does Implement Interface` first, so a trap only kills things that can actually die.

---

## 10. Rendering — 2D pixel art in UE4

Getting crisp, evenly-lit pixel art needs five things. Miss one and it looks wrong.

**Do §10.1 first.** It is the single biggest cause of blurry pixel art, and we
found it last — after chasing ortho widths and texture filters for hours.

### 10.1 Anti-aliasing — THE biggest cause of blur

**UE4 defaults to TemporalAA, which is designed for 3D and actively ruins pixel art.**

TAA blends multiple frames together to smooth edges. On pixel art that smears
adjacent texels into each other and makes everything look soft.

**Fix:** `Project Settings → Rendering → Anti-Aliasing Method → None`

Or in `Config/DefaultEngine.ini`:

```ini
r.DefaultFeature.AntiAliasing=0
```

| Method | Value | Verdict |
|---|---|---|
| **None** | `0` | ✅ **crispest — use this** |
| FXAA | `1` | ⚠️ still softens edges |
| TemporalAA | `2` | ❌ **UE4 default — the blur** |
| MSAA | `3` | ⚠️ works, costs performance |

Expect slight shimmer on thin lines while moving. That is the correct trade for
crisp pixels.

### 10.2 Texture settings (every texture)

| Setting | Value |
|---|---|
| Filter | `TF_NEAREST` (Nearest) |
| Compression | `TC_EDITOR_ICON` (UserInterface2D RGBA) |
| Mip Gen | `TMGS_NO_MIPMAPS` (No Mipmaps) |
| sRGB | on |

### 10.3 Vignette — the "some parts darker" problem

UE4 enables a **vignette** by default (`vignette_intensity = 0.4`), which darkens the
screen edges relative to the centre. On a uniform floor this reads as shading that
isn't in the art.

**Fix: an unbound `PostProcessVolume` in the level** with:

```
unbound              = True
vignette_intensity   = 0.0    override ✓
bloom_intensity      = 0.0    override ✓
auto_exposure_bias   = 0.0    override ✓
motion_blur_amount   = 0.0    override ✓
```

⚠️ **The `override_*` flags must be set to `True`** — without them the volume's values
are ignored.

⚠️ **An unbound volume OVERRIDES project renderer settings.** So set bloom etc. *in the
volume*, not only in `DefaultEngine.ini` — otherwise the volume silently re-enables
what the config disabled.

⚠️ **`r.DefaultFeature.Vignette` is not a real cvar in 4.27.** Adding it to the config
does nothing. The vignette is applied by the tonemapper; a volume is the way to control it.

### 10.4 Exposure and bloom (config)

`Config/DefaultEngine.ini` → `[/Script/Engine.RendererSettings]`:

```ini
r.DefaultFeature.AutoExposure=False
r.DefaultFeature.Bloom=False
r.DefaultFeature.MotionBlur=False
r.DefaultFeature.AmbientOcclusion=False
```

**Why auto-exposure matters:** Paper2D sprites are *unlit*, but they still pass through
tonemapping. In a level with no lights or sky the scene is mostly black, so
auto-exposure cranks up and blows out the sprites.

### 10.5 Pixel-perfect scaling — the "blurry" problem

Crispness requires **whole-number screen pixels per texel**:

```
px_per_texel = screen_width / (ortho_width / sprite_uu * sprite_px)
```

For 16px tiles at 100 uu each, at 1080p:

```
px_per_texel = 1920 / (ortho_width / 100 * 16)
```

**Only these ortho widths are crisp at 1080p** (i.e. room widths dividing 120 tiles):

| Room width | Ortho width | px/texel @1080p |
|---|---|---|
| 12 tiles | 1200 | 10.00 |
| 15 tiles | 1500 | 8.00 |
| 20 tiles | 2000 | 6.00 |
| 24 tiles | 2400 | 5.00 |
| 30 tiles | 3000 | 4.00 |
| 40 tiles | 4000 | 3.00 |

⚠️ **A 16-tile room (ortho 1600) gives 7.50 px/texel — fractional, so it shimmers.**
⚠️ **A 32-tile room (ortho 3200) gives 3.75 — also fractional.**

**Design rooms at 15, 20, 24, 30 or 40 tiles wide** to stay pixel-perfect.

### 10.6 Verifying rendering effects — a trap

**Automation screenshots cannot show post-process effects.** The default gameplay
screenshot options set `disable_tonemapping: True`, and the vignette is applied by the
tonemapper. So a scripted screenshot will show a uniform floor while PIE shows shading.

**To check a post-process effect, look at PIE directly** — or disable tonemapping in
the screenshot options.

---

## 11. Automation boundary (verified in this project)

**What Python can do:**

- Create assets: textures, sprites, flipbooks, tilemaps, tilesets, Blueprint *classes*
- Set CDO properties (movement tuning, `default_pawn_class`, camera ortho width)
- Place/position level actors, save maps
- Import art, slice sprites, build flipbooks

**What Python CANNOT do:**

| Limitation | Consequence |
|---|---|
| No Blueprint graph editing (no `K2Node`, `EdGraph`) | **All graph logic is human work** |
| **CDO components do not instantiate on spawn** | Components must be added in the editor's SCS |
| Cannot read SCS components back | A script cannot verify hand-added components |
| `KismetEditorUtilities` not exposed | Cannot force a Blueprint recompile |
| Cannot set tile collision geometry | `SpriteGeometryShape.shape_type` is read-only |
| `world_settings` not exposed | GameMode override must be set in the UI |

**Rule of thumb:** Python handles *assets and properties*; humans handle *graphs and
components*.
