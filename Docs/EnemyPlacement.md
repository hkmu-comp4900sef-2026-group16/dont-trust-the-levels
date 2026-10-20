# Enemy Placement Guide — what to place, where, and why

**Audience:** level designers and anyone placing enemies in `L_Level_00`–`L_Level_02`.
**Status (21 Oct 2026):** placement contract for the AI design in
**`Docs/EnemyAI.md`**. `BP_EnemyPlatform` and the child AI graphs are not built
yet; this is the target layout. Do not place enemies on the assumption that the
old unlimited-range or follow-off-ledge behavior still exists.

---

## 1. The one rule that matters

Walking enemies **never climb and never walk off a ledge**.

- They patrol only the platform they start on.
- A normal hit knocks them **horizontally**; they can leave a platform only by
  being pushed off and falling.
- After landing, the platform they land on becomes their new home.
- Stair rescue is **one-way downward/level only**. It never teleports an enemy
  upward.
- If a stranded enemy has no valid lower/level `BP_EnemyPlatform` within
  `RescueRadius` (500 uu), it stays on the stair step and idles. It does not
  jump into a pit.

Flying enemies (Ghost, Bat, Floating Skull) are the exception: they move in 3D
and do not use platform zones (Skull bounces; Ghost phases; Bat collides).

---

## 2. `BP_EnemyPlatform` — the level-design contract

`BP_EnemyPlatform` is an invisible marker actor. An enemy uses it as its patrol
home and as proof that a surface is a valid combat platform.

### Required setup

| Property | Setting |
|---|---|
| `Zone` | `BoxComponent`, `NoCollision`, hidden in game |
| Actor origin | **On the walking surface**, not at the platform center in Z |
| `Zone` extent Z | about `20`; the check uses a tolerance, not the box height |
| `Zone` extent X | covers the **walkable top**, never past the real edge |
| `PatrolInset` | `80` default; the enemy uses `Max(80, CapsuleRadius + 20)` |
| `bEnabled` | `true`; set `false` for safe rooms/cutscenes |
| `PlatformId` | optional debug name, e.g. `P_01_Arena` |

**Do not** place a zone on a stair step, narrow trim, a pit, a wall top, or a
moving platform. Do not let two zones overlap: `FindHomePlatform` takes the
first matching actor, so overlap makes the result order-dependent.

### Minimum zone width

The enemy keeps its capsule centre `EffectiveInset = Max(80, CapsuleRadius + 20)`
from each zone end. Use this table as the **minimum X width of the zone box**:

| Enemy | Capsule radius | Effective inset | Minimum zone width | Preferred |
|---|---:|---:|---:|---:|
| `BP_SpikeTurtle` | 70 | stationary | 200 floor, no zone needed | 250 |
| `BP_Rock1` | 70 | 90 | 400 | 450 |
| `BP_Rock2` | 60 | 80 | 350 | 400 |
| `BP_Rock3` | 45 | 80 | 300 | 350 |
| `BP_Snail` | 70 | 90 | 400 | 450 |
| `BP_ToxicSlime` | 70 | 90 | 400 | 450 |
| `BP_WoodLog` | 90 | 110 | 450 | 500 |
| `BP_Rhino` | 85 | 105 | 450 | 500 |
| `BP_Ghost` | 70 | — | no zone; room/air space | — |
| `BP_Bat` | 75 | — | no zone; ceiling + air space | — |
| `BP_FloatingSkull` | 85 | — | no zone; bounce corridor | — |

The formula is:

```text
ZoneWidth >= 2 * EffectiveInset + 2 * CapsuleRadius + 40
```

The `+40` is turn-around room. A zone narrower than the table will give the
enemy almost no travel range and can fall back to the edge-probe/stranded path.
For a 400-wide zone, set `Box Extent.X = 200`; use `Box Extent.Y` for the
platform depth and `Box Extent.Z = 20`. The actor origin Z is the floor surface.

### Spawn clearance

Place the enemy’s **capsule centre** at least `EffectiveInset` from the zone
end, and keep its feet on the surface. Do not spawn it intersecting the floor,
a wall, or the player’s start. A spawn outside the zone will not adopt that
platform.

### Y depth

The zone test uses `YSlop = 100`. Keep the enemy and the zone origin within
100 uu in Y. In a 2D level this is normally automatic; if you build two enemy
lanes at different Y depths, give each its own zone and keep them more than
200 uu apart so they cannot both match.

---

## 3. Enemy-by-enemy details

All assets live under
`/Game/DontTrustTheLevels/Enemies/Blueprints/`.
Contact damage is `1.0` for every enemy; the player currently has no health, so
contact calls `Kill`. “Health” below is the enemy’s own health, not the
player’s.

| Blueprint | Role | Movement | Detection / attack | Contact / health | Best placement |
|---|---|---|---|---|---|
| `BP_SpikeTurtle` | stationary hazard | none (`bCanMove=false`) | none; spike cycle only | `1` only when spikes out; invulnerable to player | Chokepoint, corridor pinch, timed jump |
| `BP_Rock1` | patrol + chase, splits ×2 | ground, `MoveSpeed=100` | rectangle `700×500`, de-aggro `2 s` | `1`; health `3` | Wide arena or broad floating platform |
| `BP_Rock2` | patrol + chase, splits ×2 | ground, `MoveSpeed=140` | rectangle `700×500`, de-aggro `2 s` | `1`; health `2` | Medium/broad platform |
| `BP_Rock3` | patrol + chase, final tier | ground, `MoveSpeed=180` | rectangle `700×500`, de-aggro `2 s` | `1`; health `1` | Narrower ledge (min 300) |
| `BP_Snail` | slow patrol; shell after death | ground, `MoveSpeed=50`; shell `600` for `8 s` | none | `1`; health `2`; shell invulnerable | Long flat platform with room to sweep |
| `BP_Ghost` | phasing flyer | flying, `250`; direct XZ chase | sphere `550`, no de-aggro | `1` only visible; health `2` | Room or vertical shaft, away from spawn |
| `BP_ToxicSlime` | patrol + puddle trail | ground, `MoveSpeed=70` | none | `1`; health `3` | Flat floor/corridor, not a ledge |
| `BP_Rhino` | wall-health charger | ground, `MoveSpeed=450`; horizontal charge | rectangle `1200×500`, de-aggro `2 s` | `1`; **4 wall hits**; bullets no-op | Long corridor with solid walls at both ends |
| `BP_FloatingSkull` | bouncing toggle hazard | flying, `350`; `BounceSpeed≈300` | none | `1` only when ON; health `2` | Enclosed bounce corridor, not open sky |
| `BP_Bat` | ceiling ambusher | hangs, then flying `400` | sphere `300`, no de-aggro | `1` after trigger; health `2` | Under a ceiling with clear flight space |
| `BP_WoodLog` | moving ranged shooter | ground, `MoveSpeed=90`; stops to shoot | rectangle `1400×500`, de-aggro `2 s`; fire `2.5 s` | `1`; health `3` | Long horizontal lane with clear line of fire |
| `BP_PeaPlant` | legacy/unused | none | none | — | **Do not place** |

Also do **not** hand-place `BP_EnemyBase`, `BP_RockBase`,
`BP_ShooterEnemyBase`, `BP_EnemyProjectile*`, or `BP_ToxicPuddle`; they are
bases/spawned effects, not level actors.

---

## 4. Placement notes by enemy

### 4.1 Spike Turtle — `BP_SpikeTurtle`

- It is an **environmental hazard**, not a chase enemy. It stays where placed.
- Place it on a solid, flat surface, ideally at a pinch point where the player
  must time the spike cycle.
- Give it at least **200 uu of clear floor width** (its capsule is 140 uu wide)
  so it does not visually overhang.
- Because it is permanently invulnerable to the player, never make it the only
  way to block a required path. Leave a safe gap or a timing window. Its only
  death is a `BP_KillVolume` below the arena.
- No `BP_EnemyPlatform` is needed. It does not patrol.
- Do not place it on a stair step, a moving platform, or the edge of a pit.

### 4.2 Rocks — `BP_Rock1/2/3`

- Use them on **broad platforms** where the player has room to dodge the chase.
- Put a `BP_EnemyPlatform` on the platform. Rock1 needs about `400` width,
  Rock2 `350`, Rock3 `300`.
- Rocks split into pieces that pop outward and fall. Place a broad lower
  platform with its own zone beneath them, or the pieces may become stranded.
- Do not place a rock on a stair step or a tiny floating block. It will chase to
  the edge, stop, and eventually de-aggro; that is intended but looks passive.
- If you want a “puzzle” split, place the rock near the edge of a wide platform
  and put a lower catch platform below.

### 4.3 Snail — `BP_Snail`

- It is slow and has **no detection**; it will not chase.
- Use it on a long flat platform where the player must pass it or jump over it.
- On death the shell moves at `600` for `8 s` and is invulnerable. Give the
  shell a long runway; a 400 uu platform is the minimum, 450+ is better.
- Put the zone on the platform. The shell uses the same ledge guard and must
  not sweep off the edge.
- Do not place it on a narrow ledge; the shell will turn constantly and feel
  broken.

### 4.4 Ghost — `BP_Ghost`

- It starts **invisible, harmless, and collisionless**. It only becomes a
  threat when the player enters its `550` sphere.
- Place it in a room, corridor, or vertical shaft with enough space to chase.
  It phases through `WorldStatic`, so walls will not stop it.
- Do not place it in the player’s start/safe room, and do not put it where the
  player has no warning. Add a visible tell or a `VisibleGrace` if playtests
  show it is unfair.
- No platform zone. It does not use the walker rules.
- Hidden Ghost has no collision, so a `BP_KillVolume` below will not remove it
  while hidden. Do not rely on pits to clean it up.

### 4.5 Toxic Slime — `BP_ToxicSlime`

- It patrols and leaves `BP_ToxicPuddle` tracks; it has no detection.
- Use it on flat floors and corridors where the puddle trail restricts movement.
- Put a zone on the platform; minimum width `400`.
- Do not place it on a narrow ledge or a platform with gaps: puddles spawn at
  its feet and can fall or appear in the air.
- Puddles last `3 s`; leave enough open floor for the player to route around
  them.


### 4.6 Rhino — `BP_Rhino`

- This is a **wall-health puzzle**, not a normal shootable enemy. It has 4 wall
  health; each horizontal wall hit removes 1 and turns it around; the fourth
  hit kills it. Bullets and `Kill` do nothing to it.
- Place it on a **long corridor/platform** with solid `WorldStatic` walls at
  both ends. Minimum zone width `450`; `500+` is preferred.
- The player must be able to dodge the charge and let it hit a wall four times.
  Do not put it on a short platform where it cannot build speed.
- Both walls must actually block the capsule (`WorldStatic = Block`) and have a
  mostly vertical normal (`Abs(Normal.X) > 0.7`). Do not use one-way platforms,
  thin decorative sprites, or movable walls as the rebound surface.
- It has ledge protection, but do not place it right at a stair top or a pit
  edge. If it cannot reach a wall, the puzzle cannot be completed.
- A `BP_KillVolume` below the corridor is still a good fallback.

### 4.7 Floating Skull — `BP_FloatingSkull`

- It is a **bouncing hazard**, not a chaser. It moves at `350` with a slow
  `BounceSpeed≈300` and reflects off surfaces.
- Place it in an **enclosed corridor** with walls/floor/ceiling that produce
  readable bounces. Do not place it in an open sky or a huge arena; it may fly
  away or never interact with the player.
- Its ON/OFF toggle is driven by `Event Hit`. Make sure the surfaces it is meant
  to hit are blocking.
- Contact `1` only in the ON phase; in OFF it is vulnerable and harmless.
- No platform zone. Put a `BP_KillVolume` below the bounce area in case it
  escapes.

### 4.8 Bat — `BP_Bat`

- It hangs until the player enters a `300` sphere, then plays `CeilingOut` and
  chases directly.
- Place it **under or near a ceiling**, with a clear flight path and enough
  space for the trigger sphere to be reachable. It collides with walls and
  floors; it does not phase.
- Do not set `WorldStatic = Ignore` on the Bat. That is only for Ghost.
- No platform zone. It has no de-aggro, so do not place it near a checkpoint or
  a safe room.
- Avoid narrow dead-ends where it can pin the player against a wall with no
  escape; that is difficulty, not a bug, but it should be intentional.

### 4.9 Wood Log — `BP_WoodLog`

- It patrols, stops, and fires horizontally. It is the only shooter used
  (`BP_PeaPlant` is legacy).
- Place it on a **long horizontal platform/corridor** with a clear firing lane.
  Minimum zone width `450`; `500+` is preferred.
- Detection is `1400×500`, same-platform only, de-aggro `2 s`; fire interval
  `2.5 s`.
- It does **not** aim vertically. A jumping player can dodge the shot by
  design. Place it where a standing player is in the muzzle line, not on a
  high/low perch that makes every shot miss.
- Keep the muzzle (`90` forward, `10` up) clear of walls. Do not put it behind
  a pillar or on a platform shorter than its patrol width.
- No stairs, no moving platforms, no narrow ledges.

### 4.10 Pea Plant and spawned effects

- `BP_PeaPlant` is **not part of the build**. Do not place it in a level.
- `BP_EnemyProjectile_Pea`, `BP_EnemyProjectile_Wood`, and `BP_ToxicPuddle`
  are spawned by enemies. Do not hand-place them.
- `BP_KillVolume` is a level actor: place it under every pit/void that a
  walker, Rhino, or Skull can fall into.


---

## 5. Layout recipes

### 5.1 Flat arena or wide platform

**Use:** Rocks, Snail, Toxic Slime, Wood Log, Rhino (with walls).

1. Place one `BP_EnemyPlatform` with its origin on the floor surface and its X
   box covering the walkable top.
2. Set the zone width to at least the enemy’s minimum (see §2).
3. Place the enemy near the center, feet on the floor, at least
   `EffectiveInset` from a zone end.
4. For Rhino, add solid walls at both ends and check the wall normals.
5. For Wood Log, keep a clear horizontal lane and no pillar in front of the
   muzzle.

### 5.2 Floating platform

**Use:** Rocks, Snail, Toxic Slime (if wide enough).

- Put a zone on the floating platform.
- Put a second zone on a broad lower platform beneath it. Knockback and rock
  splits can drop enemies there; the lower zone is what makes the fall safe.
- Put `BP_KillVolume` under the gap, not on the lower platform.
- Do not place Rhino or Wood Log on a small floating block; they need a long
  patrol/lane.
- Do not use a moving platform in V1. The zone is an actor and the patrol
  bounds are world-space; a mover will desynchronize them.

### 5.3 Staircase

**Do not put zones on the steps.** Do not spawn a walker on a step.

- Put a zone on the broad landing at the **top** and on the broad floor at the
  **bottom**, if those are valid combat platforms.
- If an enemy is knocked into the staircase, it becomes `Stranded`, idles, and
  `TryRescue` looks for a lower/level zone within `500` uu.
- If the nearest lower zone is farther than `500` uu, move a zone closer or
  accept that the enemy stays on the step.
- Stairs are a one-way dead end for walkers. There is no climbing back up.
- Keep a `BP_KillVolume` at the bottom only if the bottom is a real pit; a
  normal lower floor does not need one.

### 5.4 Long corridor

**Use:** Rhino, Wood Log, Floating Skull, Bat, Toxic Slime, Ghost.

- Rhino: long run-up, walls at both ends, zone width `450+`.
- Wood Log: clear horizontal firing lane, zone width `450+`.
- Skull: enclosed bounce corridor; do not leave open ends into the void.
- Bat: ceiling above the corridor; trigger sphere `300`.
- Slime: flat floor; puddles fill the route.
- Ghost: allowed, but it can phase through the corridor walls into adjacent
  rooms. Check the surrounding geometry.

### 5.5 Vertical shaft or open room

**Use:** Ghost, Bat. **Do not use walkers.**

- Ghost: `550` trigger; it chases in X/Z and can phase through walls.
- Bat: hang point near the ceiling, clear flight space, collides with geometry.
- No `BP_EnemyPlatform` is needed for either.
- Keep both away from checkpoints; neither de-aggros.

### 5.6 Pit or void

- No zone.
- No walker spawn.
- Place `BP_KillVolume` covering the pit volume.
- Flyers can cross it; Ghost hidden has no collision, so a kill volume may not
  catch it.

### 5.7 Safe room, checkpoint, cutscene

- Set `bEnabled=false` on any zone in the area, or do not place a zone.
- Do not place Ghost, Bat, Rhino, or Wood Log near the entrance; they do not
  de-aggro (or, for Rhino/Wood Log, their range is long).
- Spike Turtle is acceptable only if it is clearly inactive/avoidable.

---

## 6. Pre-flight checklist for each placed enemy

- [ ] The enemy is the correct `BP_*` child, not `BP_EnemyBase`.
- [ ] `BP_EnemyPlatform` origin is on the walking surface.
- [ ] The zone X width meets the enemy minimum in §2.
- [ ] The zone does not extend past the real floor edge.
- [ ] The enemy’s feet are on the floor; capsule is not intersecting geometry.
- [ ] The enemy starts inside the zone and at least `EffectiveInset` from an end.
- [ ] The platform has no zone on a stair step or narrow trim.
- [ ] A lower/level zone is within `500` uu if knockback can drop the enemy.
- [ ] A `BP_KillVolume` covers any pit below.
- [ ] No two zones overlap; no zone is on a moving platform.
- [ ] Rhino has two solid blocking walls with vertical normals.
- [ ] Wood Log has a clear horizontal muzzle line.
- [ ] Ghost/Bat are not in the player’s start/safe room.
- [ ] The enemy is not `BP_PeaPlant` (legacy) or a hand-placed projectile/puddle.
- [ ] PIE: patrol turns before the edge; player above does not aggro; player
      leaves and the walker de-aggros; contact kills once.

---

## 7. Quick “which enemy goes here?” table

| Geometry | Good choices | Avoid |
|---|---|---|
| Wide flat arena | Rocks, Snail, Slime, Wood Log, Rhino | — |
| Floating platform | Rock1–3, Snail, Slime (wide only) | Rhino, Wood Log on small blocks |
| Narrow ledge (300–400) | Rock3, Spike Turtle | Rhino, Wood Log, Snail shell |
| Staircase | none; zones only on landings | Any walker spawn; any zone on a step |
| Long walled corridor | Rhino, Wood Log, Skull, Bat, Slime | Ghost if it can phase into unintended rooms |
| Open vertical room | Ghost, Bat | Walkers |
| Pit/void | none (KillVolume only) | Walkers, zones |
| Safe room/checkpoint | none | Ghost, Bat, Rhino, Wood Log |
| Chokepoint | Spike Turtle, Slime | Rhino (needs run-up) |

---

## 8. Authority and related docs

- AI behavior, exact graphs and edge cases: **`Docs/EnemyAI.md`**.
- Asset inventory and per-enemy build sheets: **`Docs/Enemies.md`**.
- Ownership: placing instances is a `.umap` edit; coordinate with the Levels
  owner (`Docs/Structure.md` §4).
- Current build dependency: the contact-damage collision fix
  (`EnemyAI.md` §9) and `BP_EnemyPlatform` must exist before these placements
  behave as described.

**Do not treat the numbers as final.** `AggroHalfWidth`, speeds, `DeAggroTime`,
and `RescueRadius` are starting points; PIE-tune them after the first layout.

