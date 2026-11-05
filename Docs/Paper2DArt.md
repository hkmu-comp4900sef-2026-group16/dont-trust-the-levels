# Paper2D art pipeline (textures -> sprites -> flipbooks)

The imported pixel art now has Paper2D assets. This page records the naming,
slice geometry, and the scripts that rebuild everything.

## 1. Chain

```
T_<Name>_D  ->  SPF_<Name>_NN  ->  FLB_<Name>       (animated)
            ->  SPR_<Name>                          (single frame)
```

- `SPF_` = one sliced frame sprite.
- `SPR_` = one single-frame sprite.
- `FLB_` = flipbook made from `SPF_` frames (`frame_run = 1`).

## 2. Layout

| Pillar | Single sprites | Frames | Flipbooks |
|---|---|---|---|
| Player | `Player/Sprites/` | `Player/Sprites/Frames/` | `Player/Animations/` |
| Enemies | `Enemies/Sprites/` | `Enemies/Sprites/Frames/` | `Enemies/Animations/` |
| Traps | `Traps/Sprites/` | `Traps/Sprites/Frames/` | `Traps/Animations/` |
| Environment | `Environment/Sprites/` | `Environment/Sprites/Frames/` | `Environment/Animations/` |

Player states are character-qualified so the alternate skins never collide:

```
T_Player_MaskDude_Run_D -> SPF_Player_MaskDude_Run_00..11 -> FLB_Player_MaskDude_Run
T_Player_Appear_D       -> SPF_Player_Appear_00..06      -> FLB_Player_Appear
```

Existing Ninja Frog assets keep their original names
(`SPF_Player_Run_00`, `FLB_Player_Run`, ...).

## 3. Conventions (verified against existing assets)

| Setting | Value |
|---|---|
| `pixels_per_unreal_unit` | `0.16` (16 px = 100 uu = one tile) |
| Player / enemy pivot | `CENTER_CENTER` |
| Trap / environment prop pivot | `TOP_LEFT` |
| Idle / Fall / Jump speed | `10 fps` |
| Run / Flying / Saw speed | `14 fps` |
| Hit / Attack / Break / action speed | `12 fps` |
| Single-frame traps / props | `SPR_` (e.g. `SPR_SawOff`, `SPR_EndDoor`) |
| One-frame player / enemy states | still `SPF_` + `FLB_` so every state is uniform |

Frame size comes from the source `(WxH)` suffix. For sheets without it:
fruits and `Mushroom/Hit` infer square 32x32 frames, `Arrow` infers 18x18,
and box `Break` sheets infer 28x24. The exact inference is recorded in
`Scripts/_paper2d_manifest.json`.

## 4. Scope / exclusions

These remain plain `Texture2D` on purpose:

- `UI/Textures/T_UI_*` - UMG widgets draw textures directly.
- `T_Background_*` - background tilemap sources.
- `T_Terrain_D` and `T_SandMudIce_D` - tile atlases, not animation strips.
- `T_Enemies_20_D` - promo collage, not a sprite sheet.
- `T_Dust_D` - sampled by the `M_Dust` particle material.

Multi-cell particle/bullet textures (`*_Particle`, `*_Particles`,
`*_BulletPieces`, `*_Leafs`, `*_Bullet`) stay whole as one `SPR_`; they are
not sliced into fake animation frames.

## 5. Rebuild / verify

```powershell
# inspect the plan only (no editor)
py -3 Scripts/make_paper2d_assets.py --plan-only

# generate everything (live editor open)
py -3 Scripts/make_paper2d_assets.py --run

# one pillar or one texture at a time (resumable)
py -3 Scripts/make_paper2d_assets.py --run --group Enemies
py -3 Scripts/make_paper2d_assets.py --run --only MaskDude_Idle

# verify every sprite UV/dim/pivot/PPU and every flipbook keyframe
py -3 Scripts/_verify_paper2d.py

# rebuild the consolidated report
py -3 Scripts/_paper2d_report.py
```

The generator is idempotent: existing `SPF_`/`SPR_`/`FLB_` assets are loaded
and reused, never overwritten. Re-running after an interruption creates only
what is missing.

## 6. Current result

- 185 source textures -> **1,178 sprites/frames + 150 flipbooks = 1,328 assets**
- 1,143 animation frames
- In-engine verification: **PASS 1,328 / FAIL 0**
- Report: `Scripts/_paper2d_out.txt`
- Plan: `Scripts/_paper2d_manifest.json`

## 7. Known rounding

`T_Ghost_Hit_D` is 220x31 while its filename says 44x30. The full 31 px height
is preserved (5 frames of 44x31). Paper2D quantizes pivot points to whole
pixels, so its center pivot stores y=16 instead of the exact 15.5; that is a
half-pixel offset, not a bad slice.

Commit `.uasset` changes with the **editor closed** (see `Docs/Structure.md` 4).
