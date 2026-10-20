# Enemy AI — platforms, patrol, detection, aggro and stairs

**Status (21 Oct 2026): design locked, build sheet only.** The existing enemy
Blueprints are still shells; `BP_EnemyBase` has its shared health/damage/death
graph (43 PASS), but no child movement or detection graph is built yet. This
document supersedes the movement/detection passages in `Docs/Enemies.md` where
they disagree. The level-placement rules distilled from this document are in
**`Docs/EnemyPlacement.md`** for level designers.

**Engine:** Unreal Engine **4.27.2**, Blueprint-only, Paper2D. No C++, no
Behavior Tree, no EQS, no NavMesh. Movement is `Add Movement Input` with a
default `AIController` (Auto Possess AI = Placed In World Or Spawned).

---

## 1. Locked gameplay rules

1. **The player dies in one hit.** Every enemy contact, enemy projectile and
   toxic puddle calls `Kill` on the player. `ContactDamage` is therefore `1.0`
   everywhere; values of `2.0` are removed. The player has no health today.
2. **Walking enemies never walk off a platform.** Patrol and chase both stop
   at a ledge. A ledge is not a path. Only a **knockback** may transfer an
   enemy to another platform.
3. **After a knockback, the landing platform becomes the new home platform.**
   The enemy re-learns its patrol bounds there and stays until the next
   knockback (or death).
4. **Walking aggro uses a horizontal rectangle.** It is wide enough to cover a
   jump and shallow enough not to catch a player on the platform above/below.
   The primary cross-platform discriminator is a **same-platform check**, not
   the Z size alone.
5. **Walking enemies de-aggro.** If the player leaves the rectangle or becomes
   unreachable for `DeAggroTime`, the enemy returns to patrol.
6. **Flying aggro uses a sphere and never de-aggros.** Once a Ghost or Bat is
   triggered, it chases until it or the player dies.
7. **No pathfinding around walls.** A walker that meets a wall turns around. A
   flyer that meets a wall (Bat) stops/slides; it does not route around it.
8. **Spike Turtle is scenery, not a patrol unit.** It is stationary, has no
   detection, and cannot be damaged by the player. It only dies by falling into
   a `BP_KillVolume`.
9. **Contact damage calls `Kill`, not health damage.** Enemy health is only
   used for player weapons. No enemy damages another enemy.

---

## 2. State model

Four booleans, evaluated in this order:

| Priority | State | Flag | Meaning |
|---|---|---|---|
| 1 | Dead | `bIsDead` | base death, no movement/contact |
| 2 | Stranded | `bStranded` | landed on a non-patrol surface (stair step, prop, narrow ledge) |
| 3 | Aggro | `bAggro` | player is in range and reachable |
| 4 | Patrol | default | walk between platform bounds |

`bWasKnockedBack` is a short-lived flag set by `AnyDamage` and cleared by
`Landed`; it is not a fifth state, but it suppresses movement until landing.

Do **not** use one integer state enum. The base already has booleans, and child
blueprints need to override only one behaviour at a time (Snail shell, Rhino
wall health, Ghost phase). Booleans keep those overrides small.

---

## 3. Platform ownership — the recommended solution

### 3.1 `BP_EnemyPlatform` marker actor

Create a new `Actor` blueprint in `Enemies/Blueprints` named
`BP_EnemyPlatform`:

| Component / property | Setting |
|---|---|
| `Zone` | `BoxComponent`, no collision (`NoCollision`), hidden in game |
| `PatrolInset` | Float `80.0` — minimum edge margin; the enemy uses `Max(PatrolInset, CapsuleRadius + 20)` |
| `bEnabled` | Boolean `true` — lets a designer disable a platform |
| `PlatformId` | Name/Integer — optional debugging label |

The box covers the **walkable top surface** of one intended enemy platform. Its
`Box Extent.Z` can be small (e.g. `20`); the Z check uses a tolerance, not the
box height. Place one instance on every platform where a walking enemy is
allowed to patrol, including floating platforms. **Do not place one on stair
steps or narrow trim.**

**Zone width rule.** The enemy keeps its capsule centre `EffectiveInset =
Max(PatrolInset, CapsuleRadius + 20)` from each end. A useful patrol therefore
needs roughly:

```text
ZoneWidth >= 2 * EffectiveInset + 2 * CapsuleRadius + 40
```

If a zone is narrower, do not expect a stable patrol; it will have almost no
travel range, and the enemy may fall back to the edge-probe/stranded path. The
per-enemy minimum widths are tabulated in `Docs/EnemyPlacement.md`.

### 3.2 How an enemy finds its home

`FindHomePlatform` (called by `BeginPlay` and `Landed`):

```text
SelfFeet = Self.Location - (0,0,CapsuleHalfHeight)
Get All Actors of Class (BP_EnemyPlatform)
ForEach:
  Branch: Platform.bEnabled
  Branch: PointInPlatformZone(SelfFeet, Platform, 40)
    True -> Candidate = Platform; break/return
Branch: Candidate valid
  True  -> Set HomePlatform = Candidate
           Set EffectiveInset = Max(Candidate.PatrolInset, CapsuleRadius + 20)
           Set PatrolMinX = Candidate.X - Extent.X + EffectiveInset
           Set PatrolMaxX = Candidate.X + Extent.X - EffectiveInset
           Set bStranded = false
  False -> Set HomePlatform = None
           # no zone is not an error: edge-probe patrol still works.
           # Trace down to set GroundZ; if there is no floor, wait for Landed.
           # Only a landing on a too-narrow surface makes the enemy stranded.
```

`PointInPlatformZone(Point, Platform, ZTolerance)` is a pure function:

```text
Break Vector (Point)
Platform.GetActorLocation -> Break Vector
Return: Abs(Point.X - Platform.X) <= BoxExtent.X
        AND Abs(Point.Y - Platform.Y) <= YSlop (100)
        AND Abs(Point.Z - Platform.Z) <= ZTolerance
```

`PointInPlatformXZ(Point, Platform)` is the same X/Y test without the Z
tolerance; use it before the downward ground trace.

The **actor origin of `BP_EnemyPlatform` must sit on the platform surface**;
the `Zone` box extends ±20 around it. Then `Platform.Z` is the surface Z.

`IsPlayerOnHomePlatform` must handle a player **jumping above** the platform.
Do not use the 40 uu landing tolerance for that. Use an XZ test plus a
downward ground trace:

```text
PlayerFeet = Player.Location - (0,0,PlayerCapsuleHalfHeight)
Branch: PointInPlatformXZ(PlayerFeet, HomePlatform) -> false: return false
TraceStart = Player.Location
TraceEnd   = Player.Location
             - (0,0, PlayerCapsuleHalfHeight + PlayerGroundProbeDepth)
LineTraceSingleByChannel (Visibility or WorldStatic)
Branch: no hit -> return false
Return Abs(Hit.Z - HomePlatform.Z) <= 40
```

`PlayerGroundProbeDepth` should cover the player's jump/double-jump (start
with `600`). A jumping player above the same platform still traces down to it;
a player standing on the platform above traces to a different Z; a player over
a gap gets no hit. This is the reliable reachability gate.

If `HomePlatform` is `None` (no zones authored), replace
`PointInPlatformXZ(PlayerFeet, HomePlatform)` with
`Abs(Player.X - Self.X) <= AggroHalfWidth` and compare the trace Z to
`GroundZ` instead of `HomePlatform.Z`. The rest is identical. This fallback can
false-positive across two same-height platforms separated by a gap; add a
downward trace at the midpoint between enemy and player (no hit = gap) or
author zones to avoid it.

### 3.3 Why this is better than guessing geometry

- The level designer explicitly says which surfaces are valid enemy platforms.
- A floating platform is just another zone; patrol bounds come from its box.
- Stairs are simply not zones, so an enemy knocked into a stair step is
  `Stranded` instead of thinking the step is a valid patrol route.
- The rescue destination is guaranteed to exist and be broad; no downward trace
  can accidentally choose a hole or a 100 uu step.
- `IsPlayerOnHomePlatform` is a reliable reachability test, not a Z guess.

**Ownership note:** `BP_EnemyPlatform` is an Enemies-pillar asset; placing its
instances is a `.umap` edit and must be coordinated with the Levels owner
(`Docs/Structure.md` §4).


---

## 4. Variables to add to `BP_EnemyBase`

Add these in **My Blueprint → Variables**. Existing variables are in
`Enemies.md` §3.2.

| Name | Type | Default | Purpose |
|---|---|---|---|
| `MoveSpeed` | Float | `100.0` | **existing** — child-specific patrol speed |
| `ChaseSpeed` | Float | `150.0` | walker aggro speed; `0` = never chase |
| `bAggro` | Boolean | `false` | runtime |
| `bStranded` | Boolean | `false` | landed off a valid platform |
| `bWasKnockedBack` | Boolean | `false` | suppresses AI until `Landed` |
| `AggroHalfWidth` | Float | `600.0` | rectangle half-width; walkers |
| `AggroHalfHeight` | Float | `500.0` | rectangle half-height; covers jump/double-jump |
| `AggroRadius` | Float | `0.0` | sphere radius; flyers (`0` = disabled) |
| `DeAggroTime` | Float | `2.0` | walker only; seconds unreachable/out of range |
| `UnreachableTime` | Float | `0.0` | runtime accumulator |
| `MaxChaseStepZ` | Float | `500.0` | vertical tolerance while the ground trace confirms the platform |
| `bRequireAggroLineOfSight` | Boolean | `false` | optional wall trace |
| `LedgeProbeAhead` | Float | `30.0` | forward probe distance |
| `LedgeProbeDepth` | Float | `80.0` | downward probe length |
| `MaxPatrolStepZ` | Float | `15.0` | flat-platform tolerance |
| `GroundZ` | Float | `0.0` | current platform surface Z |
| `PlayerGroundProbeDepth` | Float | `600.0` | reachability trace below player |
| `HomePlatform` | Actor | `None` | `BP_EnemyPlatform` reference |
| `PatrolMinX` | Float | `0.0` | runtime world-space bound |
| `PatrolMaxX` | Float | `0.0` | runtime world-space bound |
| `RescueRadius` | Float | `500.0` | stranded search radius |
| `MinPatrolWidth` | Float | `300.0` | fallback width scan only; override per child (Rhino/Wood Log `450`) |
| `MaxPatrolWidth` | Float | `600.0` | fallback width scan only |
| `MaxDrop` | Float | `500.0` | fallback safe-drop probe only |

Child defaults override `MoveSpeed`, `ChaseSpeed`, the aggro box/sphere and
`DeAggroTime`. Do **not** set `MaxWalkSpeed` in children any more; the movement
functions set `MaxWalkSpeed = MoveSpeed` or `ChaseSpeed`.

---

## 5. Patrol (walkers)

`PatrolStep` runs from `Event Tick` when
`NOT bIsDead AND NOT bStranded AND NOT bAggro AND bCanMove`:

```text
Branch: HomePlatform valid?
  False -> skip the min/max checks and use only the ledge probe below
  True  ->
    Branch: Self.X <= PatrolMinX AND Facing < 0 -> SetFacing(+1)
    Branch: Self.X >= PatrolMaxX AND Facing > 0 -> SetFacing(-1)
    Branch: LedgeAhead() -> False: SetFacing(-Facing); return
    Add Movement Input ((Facing,0,0), 1)
```

`LedgeAhead` is the safety net even when a zone exists:

```text
Start = Self.Location + (Facing * (CapsuleRadius + LedgeProbeAhead), 0,
                         -CapsuleHalfHeight + 10)
End   = Start + (0,0,-LedgeProbeDepth)
LineTraceSingleByChannel (Visibility or WorldStatic)
Branch: no hit -> return false
Branch: Abs(Hit.Z - GroundZ) > MaxPatrolStepZ -> return false
Branch: Hit.Normal.Z < 0.7 -> return false
return true
```

`GroundZ` is `SelfFeet.Z` when the enemy lands or adopts a platform. A wall does
not need a separate forward trace: `Event Hit` with `Abs(Normal.X) > 0.7`
reverses `Facing`, and the ledge probe stops it before a drop. Add a `0.1 s`
turn cooldown so two edge probes in one frame cannot flip it twice.

**Floating platforms:** the zone bounds stop the enemy at the platform edge.
The ledge probe also sees no floor beyond the edge. The enemy never walks down
unless `bWasKnockedBack` is true.

---

## 6. Detection, chase and de-aggro

### 6.1 Geometry

**Walking enemies — rectangle** (math, no extra component):

```text
Player valid?
Abs(Player.X - Self.X) <= AggroHalfWidth
AND Abs(Player.Z - Self.Z) <= AggroHalfHeight
AND Abs(Player.Y - Self.Y) <= 100          # 2D game safety
AND IsPlayerOnHomePlatform()               # primary cross-platform gate
AND (NOT bRequireAggroLineOfSight OR clear line trace)
```

**Flying enemies — sphere**:

```text
VSize((Player - Self) with Y = 0) <= AggroRadius
```

Use a wide rectangle for walkers, not a sphere: a sphere with radius 600 would
reach 600 uu above and aggro through the floor above. The rectangle's
`AggroHalfHeight` is tuned to cover a jump on the **same** platform; the
same-platform gate means it cannot aggro a player standing on a different
platform even if the boxes overlap.

### 6.2 Reachability

A walker may only chase when all are true:

- player is inside the aggro rectangle;
- `IsPlayerOnHomePlatform()` is true;
- `Abs(Player.Z - Self.Z) <= MaxChaseStepZ`;
- optional: a horizontal line trace to the player is clear.

If the player is on another platform, jumping across a gap, or falling into a
pit, the enemy **stands at the ledge** and does not follow.

### 6.3 Aggro loop

```text
Event Tick:
  Branch: bIsDead OR bStranded -> return
  Branch: bWasKnockedBack -> return
  Player = Get Player Character(0)
  InBox = IsPlayerInAggroBox(Player)
  Reachable = InBox AND IsPlayerOnHomePlatform(Player)
                  AND Abs(Player.Z - Self.Z) <= MaxChaseStepZ
  Branch: Reachable
    True  -> Set bAggro = true
             Set UnreachableTime = 0
             ChaseStep(Player)
    False ->
      Branch: bAggro
        True  -> Set UnreachableTime += DeltaSeconds
                 Branch: UnreachableTime >= DeAggroTime
                   True  -> Set bAggro = false
                            Set UnreachableTime = 0
                            Set MaxWalkSpeed = MoveSpeed
                            RefreshStateFlipbook
                   False -> stop movement, face player if visible
        False -> PatrolStep()
```

`ChaseStep`:

```text
SetFacing(Player.X - Self.X)
Branch: LedgeAhead() -> False: stop movement; return   # stand at edge
Add Movement Input ((Facing,0,0), 1)
```

If the player jumps over the enemy, `Player.X - Self.X` flips and the enemy
turns. It does not jump, path around a wall, or step down.

**De-aggro rule:** after `DeAggroTime` seconds of the player being out of range
or unreachable, `bAggro=false` and the enemy resumes patrol from its current
position. If the player returns to a reachable spot inside the rectangle, the
enemy re-aggros immediately. `UnreachableTime` resets whenever the player is
reachable again.

**Flying aggro has no de-aggro path.** Ghost and Bat never run the de-aggro
branch.


### 6.4 Suggested defaults

| Enemy | Detection | Width / radius | Height | De-aggro | Chase |
|---|---|---|---|---|---|
| Rock1/2/3 | rectangle | `700` | `500` | `2.0 s` | yes |
| Rhino | rectangle | `1200` | `500` | `2.0 s` | yes (charge) |
| Wood Log | rectangle | `1400` | `500` | `2.0 s` | no — stops to shoot |
| Ghost | sphere | `550` | — | **never** | yes, through walls |
| Bat | sphere | `300` | — | **never** | yes, collides |
| Snail | none | — | — | — | no |
| Toxic Slime | none | — | — | — | no |
| Spike Turtle | none | — | — | — | no |
| Floating Skull | none | — | — | — | no |

The `500` height is intentional: it covers the player's jump/double-jump. It
does **not** cause cross-platform aggro because `IsPlayerOnHomePlatform()` is
part of the reachability test. Tune the width/speed after PIE.

---

## 7. Knockback, landing, stranded surfaces and stairs

### 7.1 Knockback

In `AnyDamage`, before `LaunchCharacter`:

```text
Set bWasKnockedBack = true
Set bAggro = false
Set bStranded = false
Set MaxWalkSpeed = MoveSpeed
Set UnreachableTime = 0
LaunchCharacter(...)
```

Do not clear `bWasKnockedBack` with a single fixed timer. A character can be in
the air for a variable time, and a purely horizontal hit may **not leave the
floor at all** — in that case `Event Landed` never fires and the enemy would
stay frozen. Resolve it in two places:

- `Event Landed` -> `ResolveKnockback`;
- `Event Tick`: if `bWasKnockedBack` and `CharacterMovement.IsFalling()` is
  false, call `ResolveKnockback` immediately (the hit stayed on the floor).

`ResolveKnockback` is the body in §7.2 (clear flag, find/adopt platform).

### 7.2 Landing

`ResolveKnockback` (called by `Event Landed` **and** by the Tick fallback in
§7.1):

```text
Set bWasKnockedBack = false
Set bAggro = false
Set UnreachableTime = 0
FindHomePlatform()
Branch: HomePlatform valid
  True  -> AdoptPlatform()
           Set bCanMove = true
           Set GroundZ = SelfFeet.Z
           Set Facing = 1 (or preserve)
           RefreshStateFlipbook()
  False -> MeasurePlatformWidth()        # runtime fallback, EnemyAI.md §7.4
           Branch: Width >= MinPatrolWidth
             True  -> Set bStranded = false
                      Set bCanMove = true
                      Set GroundZ = SelfFeet.Z
                      RefreshStateFlipbook()
             False -> Set bStranded = true
                      Set bCanMove = false
                      PlayStateFlipbook(IdleFlipbook, true)
                      Set Timer by Function Name("TryRescue", 0.5, false)
```

Because `FindHomePlatform` runs after **every** landing, a rock knocked onto a
lower platform adopts that platform as its new home. It stays there until the
next knockback, exactly as requested.

### 7.3 Stairs: the safe recommendation

A stair step is a narrow platform. The enemy may be knocked into one but must
not patrol off it. With the zone model, the step has no `BP_EnemyPlatform`, so
the enemy becomes `Stranded`, stops, and idles instead of pacing a 100 uu box.

`TryRescue`:

```text
Branch: bIsDead -> return
Get All Actors of Class (BP_EnemyPlatform)
ForEach:
  Branch: Platform.bEnabled
  Branch: 2D distance(Self, Platform) <= RescueRadius
  Branch: Platform.Z < Self.Z + 50            # below or level, not above
  Keep nearest valid Candidate
Branch: Candidate valid
  True  -> SetActorLocation(Candidate.Location + (0,0,120),
                            bSweep=false, bTeleport=true)
           Set Movement Mode (Falling)
           # gravity drops it onto a guaranteed broad platform
           # Event Landed runs FindHomePlatform again and adopts it
  False -> stay stranded (idle); no suicide drop
```

The teleport/drop is deliberate: the destination is an authored zone, so it
cannot be a hole or a 100 uu step. A short `Set Actor Hidden In Game` or a dust
puff can hide the reposition later. Do not trace blindly downward and walk off;
that is how enemies kill themselves.

**This is deliberately one-way: rescue never teleports upward.** A normal hit
uses horizontal knockback (`LaunchCharacter(X, 0, 0, bZOverride=false)`), so a
walker leaves its platform only by being pushed off and falling. It cannot
climb stairs or get back up to a higher platform. If you ever want upward
rescue, add `bAllowRescueUp` / `RescueMaxRise` and change the candidate test to
`Abs(Platform.Z - Self.Z) <= RescueMaxRise`; keep the default off, because
teleporting up can bypass level design and looks unnatural.

If no zone is in range, **staying on the stair step is the safe fallback**. It
looks odd but is safe, and it is better than falling into a pit. For final
polish, either add a zone on a nearby broad platform or despawn the stranded
enemy after a long timeout (only if it is not required for progression).

**Is it hard?** The zone actor plus rescue is a medium-sized Blueprint job:
roughly 4–6 hours including level placement and PIE tuning. A runtime-only
solution (downward trace + width scan) is possible but has more edge cases and
takes longer to make reliable. Keeping enemies on the stair step is the
lowest-cost V1, provided they stand still and are not unkillable blockers.

### 7.4 Runtime-only fallback (if zones are rejected)

If you do not want to place zones, `MeasurePlatformWidth` does this:

1. Downward trace at `Self.X`, `Self.X ± 25`, `±50`, `±100`, `±200`, up to
   `MaxPatrolWidth` (e.g. `600`).
2. Accept a sample only if it hits walkable ground within
   `MaxPatrolStepZ` of `GroundZ`.
3. Width = rightmost accepted sample − leftmost accepted sample.
4. If width `< MinPatrolWidth`, mark `Stranded`.
5. To drop safely, probe downward from both edges up to `MaxDrop` (e.g. `500`).
   If a hit exists, run the same width scan at that lower Z. Only drop if the
   lower width is `>= MinPatrolWidth`.
6. Otherwise stay.

This is feasible, but it is more graph nodes, more traces per landing, and more
ways to misclassify decorative geometry. The zone model is the recommended
authoring contract.


---

## 8. Per-enemy changes

| Enemy | Movement | Detection / aggro | Contact | Health / death | Special |
|---|---|---|---|---|---|
| `BP_SpikeTurtle` | **stationary**, no patrol | none | `1` only while spikes out | invulnerable to player; `KillVolume` only | spike cycle stays; `bDealContactDamage = bSpikesOut` |
| `BP_Rock1/2/3` | patrol + chase | rectangle `700×500`, de-aggro `2 s` | `1` | `3 / 2 / 1`, split | `ChildRockClass`; pieces adopt landing platform |
| `BP_Snail` | patrol; shell patrols | none | `1` (not `2`) | `2`, shell after death | shell invulnerable, ledge-bound, `8 s` life |
| `BP_Ghost` | fly, chase through walls | sphere `550`, no de-aggro | `1` only visible | `2` | invisible at first; visible/hidden loop after aggro |
| `BP_ToxicSlime` | patrol | none | `1` | `3` | puddle timer unchanged |
| `BP_Rhino` | patrol + charge | rectangle `1200×500`, de-aggro `2 s` | `1` | **4 wall health**; bullets no-op | each wall hit `-1` and turn |
| `BP_FloatingSkull` | bounce | none | `1` only when ON | `2` | `BounceSpeed ≈ 300`; ON/OFF toggle stays |
| `BP_Bat` | hang, then fly | sphere `300`, no de-aggro | `1` only after trigger | `2` | collides with wall/floor |
| `BP_WoodLog` | patrol; stops to shoot | rectangle `1400×500`, de-aggro `2 s` | `1` | `3` | horizontal shots only |
| `BP_PeaPlant` | unused | — | — | — | keep out of build order |

### 8.1 Spike Turtle

- `bCanMove=false`; no patrol Tick and no detection.
- `bUseHealth=false`, `bInvulnerable=true` permanently.
- `SpikeCycle`/`FinishSpikeChange` remain, but `FinishSpikeChange` sets
  `bDealContactDamage = bSpikesOut` and `ContactDamage = 1.0` (never `2.0`).
- Player bullets and `Kill` are no-ops. A `BP_KillVolume` below the arena
  destroys it by tag if it falls.
- It is an environmental hazard: sometimes dangerous, never a chase target.

### 8.2 Rocks

- Add the rectangle aggro/de-aggro loop from §6.
- `MoveSpeed`/`ChaseSpeed` per tier; keep the existing `100 / 140 / 180`
  identities and tune the chase values separately.
- Split pieces are spawned with `LaunchCharacter`; each piece runs `Landed` and
  adopts the platform it lands on (or becomes stranded/rescued). Do not assume
  the parent's `HomePlatform` is still valid.

### 8.3 Snail

- Keep the normal patrol and the shell death override.
- No detection and no chase. Add the ledge guard to both the normal body and
  the shell; a shell must sweep the platform, not fall off it.
- `ShellContactDamage` must be `1.0`, not `2.0`.
- Shell remains invulnerable and self-destructs after `ShellLifetime`.

### 8.4 Ghost

- **Before aggro:** `bInvisible=true`, `Sprite0` hidden, `CollisionCylinder`
  `NoCollision`, `bInvulnerable=true`, `bDealContactDamage=false`. It hovers
  idle; it does not chase.
- On player entering the sphere: `bAggro=true`; become visible; enable
  collision; set `bInvulnerable=false`; `bDealContactDamage=true`; start the
  visible/hidden loop.
- **Visible phase:** sprite visible, collision enabled with
  `WorldStatic = Ignore` (phases through walls), contact channel as chosen,
  vulnerable, contact `1`.
- **Hidden phase:** sprite hidden, capsule **and `ContactBox`** collision off,
  invulnerable, contact off. It still moves toward the player; it just cannot be
  hit or hit. On the visible phase, re-enable `ContactBox` (`QueryOnly`,
  `Pawn=Overlap`) with the capsule.
- The chase is direct: `Direction = Normalize(Player - Self)` in the X/Z plane,
  `Add Movement Input(Direction, 1)`. No pathfinding around walls.
- No de-aggro. The loop continues until death.
- If the player is inside the ghost when it becomes visible, the contact kill
  is legal; add a short `VisibleGrace` if playtesting shows it is unfair.


### 8.5 Toxic Slime

- Keep the patrol and puddle timer. No detection and no chase.
- Add the ledge guard; it must not walk onto a lower step or into a pit.
- Contact `1`. Puddle kill unchanged; puddles are player-only.

### 8.6 Rhino

- Replace the old invulnerable wall-kill. New contract:
  - `MaxHealth=4`, `CurrentHealth=4`, `bUseHealth=true`;
  - `bInvulnerable=true` so player bullets and `Kill` are ignored;
  - `WallHitCooldown=0.5`, `LastWallHitTime=-1000`.
- On `Event Hit` with `Abs(Normal.X)>0.7` and `OtherActor != Player`:

```text
Branch: now - LastWallHitTime < WallHitCooldown -> return
Set LastWallHitTime = now
Set CurrentHealth -= 1
SetFacing(-Facing)                       # turn around after hitting wall
PlayStateFlipbook(HitWallFlipbook, false)
Branch: CurrentHealth <= 0
  True  -> Set bInvulnerable = false
           Die
  False -> Set Timer by Function Name("EndWallHit", 0.3, false)
```

- `EndWallHit` resumes charge/patrol (`RefreshStateFlipbook`).
- Detection is the long horizontal rectangle (`1200×500`) and uses the same
  platform/de-aggro rules. It charges horizontally, never vertically.
- Contact `1`. Bullets never damage it. Falling into a `BP_KillVolume` still
  destroys it by tag.

### 8.7 Floating Skull

- Keep the ON/OFF toggle and `Event Hit` reflection.
- `BounceSpeed` is now a **slow** bounce: `≈300` (bullet speed is `900`).
  Keep the Z component of the reflection; do not add gravity.
- No detection, no chase. Contact only when ON; `1` damage.
- If it falls into a pit, `BP_KillVolume` removes it.

### 8.8 Bat

- Trigger sphere is smaller than Ghost: `300` (was `350` and effectively
  larger because of the old distance check).
- After the `CeilingOut` animation, `bChasing=true` and it chases directly in
  the X/Z plane. Unlike Ghost, it **collides with walls and floors**: do not set
  `WorldStatic = Ignore`. If it hits a wall, it stops/slides; there is no
  pathfinding.
- No de-aggro. Contact `1` only after the trigger.
- It is a normal health enemy (`2`) and can be shot down.

### 8.9 Wood Log

- Replace unlimited-range fire with the rectangle detection in §6:
  `1400×500`, same platform, `DeAggroTime=2.0`.
- It **stops and shoots** while aggro; it does not chase around the platform.
  `TryFire` is gated by `bAggro`, not by "player exists anywhere".
- It only fires horizontally: projectile direction `(Facing,0,0)`, muzzle Z
  fixed by `MuzzleOffset.Z`. Do not aim at the player's Z.
- If the player leaves the rectangle or becomes unreachable for `DeAggroTime`,
  `bAggro=false`, `EndAttack`, resume patrol. If the player re-enters while
  reachable, re-aggro.
- No vertical aim means a jumping player can dodge; that is intended.
- Contact `1`; health `3`.


---

## 9. Contact damage: the current graph has a blind spot

**Finding (21 Oct 2026):** `BP_EnemyBase`'s `Event ActorBeginOverlap` is bound to
the inherited capsule, but both `BP_EnemyBase` and `BP_Player` use the `Pawn`
collision preset with `Pawn = Block`. Unreal only generates overlap events when
at least one side is `Overlap`. **The contact-damage event therefore never
fires against the player**, even though the graph and the 43-PASS verifier are
structurally correct.

Choose one fix:

| Option | What | Trade-off |
|---|---|---|
| **A (recommended)** | Add a `ContactBox` (`BoxComponent`) to `BP_EnemyBase`: `QueryOnly`, `Generate Overlap Events`, `Pawn = Overlap`, all other channels `Ignore`, extents slightly larger than the capsule. Bind **On Component Begin Overlap (ContactBox)** to the existing contact chain. | Keeps the capsule solid; one hand-added SCS component; child `Event Hit` wall logic is untouched. Ghost must disable it while hidden. |
| **B (simplest)** | Keep the capsule, set `Pawn = Overlap` in the `Pawn` preset, keep `WorldStatic/WorldDynamic = Block`. | No new component, but enemies and player pass through each other; enemies can overlap/pile visually. |
| **C** | Use the capsule's `Event Hit` with `OtherActor == Player` to call `Kill`. | No new component, but no `BeginOverlap` semantics; less reliable for spawn/overlap and needs a cooldown. |

With **A**, the contact event must be the component-overlap event
(`On Component Begin Overlap`), not the actor-level `ReceiveActorBeginOverlap`.
The existing actor event can stay unused or be deleted. Keep the
player-equality gate and the `ContactDamageCooldown`; the gate is what stops
enemy-vs-enemy damage.

`ContactDamage` is `1.0` on every enemy. Remove the old `2.0` values from the
turtle and snail shell.

---

## 10. Build order

0. **Contact fix first.** Add `ContactBox` (option A) or set `Pawn = Overlap`
   (option B), then PIE-test one enemy touching the player. Do not build child
   AI on a dead contact event.
1. **`BP_EnemyPlatform`** — box marker, hidden in game, no collision.
2. **`BP_EnemyBase` additions** — new variables, `FindHomePlatform`,
   `AdoptPlatform`, `PointInPlatformZone`, `IsPlayerOnHomePlatform`,
   `PointInPlatformXZ`, `LedgeAhead`, `PatrolStep`, `ChaseStep`,
   `IsPlayerInAggroBox`, `IsPlayerInAggroSphere`, `UpdateAggro`, `Landed`,
   `ResolveKnockback`, `MeasurePlatformWidth`, `TryRescue`.
3. **`BP_EnemyProjectile` → `BP_ToxicPuddle` → `BP_ShooterEnemyBase`** — the
   pending work from `Enemies.md` §7.1; projectile/puddle kill is independent of
   the AI rework.
4. **`BP_WoodLog`** — detection/de-aggro + horizontal fire; then the other
   children.
5. **Children** — per §8.
6. **PIE tuning** — platform placement (`Docs/EnemyPlacement.md`),
   `AggroHalfWidth/Height`, speeds, de-aggro time, rescue radius.

---

## 11. Test matrix

| # | Setup | Expected |
|---|---|---|
| 1 | Enemy touches player | player dies once; no enemy-vs-enemy kill |
| 2 | Patrol on a floating platform | turns before the edge; never steps down |
| 3 | Player stands on platform above | no aggro; no chase |
| 4 | Player jumps over an aggroed walker on the same platform | walker turns, does not jump/step off |
| 5 | Player drops to a lower platform | walker stops at edge; after `DeAggroTime` resumes patrol |
| 6 | Player returns to the walker's platform | walker re-aggros and chases |
| 7 | Shoot a walker off the platform | it lands on the lower broad platform and adopts it as home |
| 8 | Knock an enemy into a stair step | it becomes stranded, idles, then drops to the nearest zone if one exists |
| 9 | No zone below a stair step | it stays stranded; it never jumps into a pit |
| 10 | Spike Turtle | stationary, no detection, bullets do nothing; `KillVolume` kills |
| 11 | Rock | patrols/chases, splits, pieces adopt their landing platform |
| 12 | Ghost before trigger | invisible, no collision, no contact, no chase |
| 13 | Ghost after trigger | visible/hidden loop, phases through walls, no de-aggro |
| 14 | Bat after trigger | flies directly, collides with walls/floor, no de-aggro |
| 15 | Rhino | takes 4 wall hits, turns each time, dies on the 4th; bullets do nothing |
| 16 | Wood Log | fires only inside its rectangle, only horizontally, de-aggros and resumes patrol |

---

## 12. Known limits

- **No pathfinding.** Walkers turn at walls; they do not route around them.
  Flyers with collision (Bat) can get stuck against a wall. This is accepted.
- **No NavMesh.** Do not add one for this; the platform-zone model is simpler
  and does not fight Paper2D/moving traps.
- **Platform zones are level-authored.** If a platform has no zone, enemies
  treat it as invalid and will not patrol there.
- **Stranded rescue can look like a teleport.** Hide it with a puff/VFX later,
  or place zones so the nearest lower zone is close.
- **The player has no health.** Contact/projectile/puddle all call `Kill`.
- **Contact overlap needs the fix in §9.** The current 43-PASS verifier checks
  graph structure, not collision responses.
- **All numbers are starting points.** PIE-tune after the first placement.

