# Enemy AI — platforms, patrol, detection, aggro and stairs

**Status (5 Nov 2026): shared base AI complete; walker PIE pending.**
`BP_EnemyBase` has its shared health/damage/death graph, the `ContactBox`
contact fix, and the full AI core (**44 PASS / 0 FAIL / 2 PENDING** until the
acquire/keep paste lands; then 46 PASS). All **13/13** functions and **25/25**
§4 variables exist with the documented defaults
(`_check_enemy_ai_vars.py`: 25 PASS). The aggro-on-hit change is landed:
`UpdateAggro` is **54 nodes**, with the box term and the post-hit term feeding a
`BooleanOR` before the aggro branch; `_verify_enemy_base.py` now fails if any of
the three old links returns. The **acquire/keep split** is staged as
`Scripts/_bp_enemy_base_aggro_keep_paste.txt` (**+7 nodes → 61**): paste it into
`UpdateAggro`, compile, save, then `Scripts/_run_aggro_keep_check.py` must print
`RESULT: PASS` (§6.2). `BP_Snail` overrides `ChaseSpeed=250`
(`80` before the 7 Nov 2026 retune), `AggroHalfWidth=0`, `AggroHalfHeight=0` and
`bAggroOnHit=true` (saved 5 Nov);
its remaining health/movement/flipbook defaults are still open. `BP_EnemyPlatform`
auto-placement works (7 auto zones in `L_Level_01`). The next work item is PIE
tests 1–9 and the `M1 GREEN` line, not another child enemy. This document
supersedes the movement/detection passages in `Docs/Enemies.md` where they
disagree. The level-placement rules distilled from this document are in
**`Docs/EnemyPlacement.md`** for level designers. The three-person execution
split, gates and asset locks are in **`Docs/EnemyWorkPlan.md`**.

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
5. **Walking enemies de-aggro only when the player is unreachable.** If the
   player leaves the enemy's platform or becomes unreachable for `DeAggroTime`,
   the enemy returns to patrol. Running along the same platform never starts
   that clock, however far past `AggroHalfWidth`: the rectangle only *starts* a
   chase, it does not end one (§6.2).
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
| 3 | Aggro | `bAggro` | player was detected and is still reachable (same platform) |
| 4 | Patrol | default | walk between platform bounds |

`bWasKnockedBack` is a short-lived flag set by `AnyDamage` and cleared by
`ResolveKnockback` (called from `Event On Landed` or the Tick fallback); it is
not a fifth state, but it suppresses movement until landing is resolved.

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

> **Current asset check (24 Oct 2026):** `BP_EnemyPlatform` has `Zone`,
> `PatrolInset = 80`, `PlatformId` and `bEnabled = true`; the old `bEnable`
> name is gone. A live spawn check confirms `Zone` is a `BoxComponent` with
> `extent (50,50,20)`, `NoCollision` and hidden in game. `FindHomePlatform`
> can read `bEnabled` directly.

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

`FindHomePlatform` (called by `BeginPlay` and `Event On Landed`):

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
           # Trace down to set GroundZ; if there is no floor, wait for Event On Landed.
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

`PlayerLocation` in this pseudocode is a **function-local** filled once from
`Get Actor Location(PlayerRef)`. Do not look for a `PlayerLocation` member
variable or a `GetPlayerLocation` function in `BP_EnemyBase`; neither exists.

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
| `bWasKnockedBack` | Boolean | `false` | suppresses AI until `ResolveKnockback` clears it |
| `AggroHalfWidth` | Float | `600.0` | rectangle half-width; walkers — **acquire only** (§6.2) |
| `AggroHalfHeight` | Float | `500.0` | rectangle half-height; covers jump/double-jump |
| `AggroRadius` | Float | `0.0` | sphere radius; flyers (`0` = disabled); `> 0` also means "never de-aggro" |
| `DeAggroTime` | Float | `2.0` | walker only; seconds off-platform/unreachable |
| `UnreachableTime` | Float | `0.0` | runtime accumulator |
| `MaxChaseStepZ` | Float | `500.0` | vertical tolerance while the ground trace confirms the platform |
| `bRequireAggroLineOfSight` | Boolean | `false` | optional wall trace |
| `bAggroOnHit` | Boolean | `false` | walker only; chase for `DeAggroTime` after a hit, even outside the box |
| `LedgeProbeAhead` | Float | `30.0` | forward probe distance |
| `LedgeProbeDepth` | Float | `80.0` | downward probe length |
| `MaxPatrolStepZ` | Float | `15.0` | flat-platform tolerance |
| `GroundZ` | Float | `0.0` | current platform surface Z |
| `PlayerGroundProbeDepth` | Float | `600.0` | reachability trace below player |
| `HomePlatform` | `BP_EnemyPlatform` object reference | `None` | current home zone |
| `PatrolMinX` | Float | `0.0` | runtime world-space bound |
| `PatrolMaxX` | Float | `0.0` | runtime world-space bound |
| `RescueRadius` | Float | `500.0` | stranded search radius |
| `MinPatrolWidth` | Float | `300.0` | fallback width scan only; override per child (Rhino/Wood Log `450`) |
| `MaxPatrolWidth` | Float | `600.0` | fallback width scan only |
| `MaxDrop` | Float | `500.0` | fallback safe-drop probe only |

Child defaults override `MoveSpeed`, `ChaseSpeed`, the aggro box/sphere and
`DeAggroTime`. Do **not** set `MaxWalkSpeed` in children any more; the movement
functions set `MaxWalkSpeed = MoveSpeed` or `ChaseSpeed`.

### 4.1 What is not a member variable

`EffectiveInset`, `BestDistance`, `Candidate`, `SelfFeet`, `PlayerFeet`,
`BoxExtent` and the trace hit/start/end values are **function-locals**. Compute
them inside `FindHomePlatform`, `LedgeAhead` or `TryRescue`; do not add them as
Blueprint variables.

`IsPlayerOnHomePlatform` uses four locals for the same reason: `PlayerRef`
(Character), `PlayerLocation` (Vector), `HalfHeight` (Float), `TargetZ`
(Float). Add them in the function's **Local Variables** panel, not in
My Blueprint → Variables. There is **no `PlayerLocation` member variable and no
`GetPlayerLocation` function** in `BP_EnemyBase`; the `Get PlayerLocation`
getter only appears after the local is added, and the actual location read is
`Get Actor Location` with `PlayerRef` as Target.

`HomePlatform` should be typed as a **`BP_EnemyPlatform` object reference**, not
a generic `Actor` reference. That lets you read `Zone`, `PatrolInset` and
`bEnabled` directly, without a Cast node at every use. If you already added it
as `Actor`, either change the type or add one Cast in `FindHomePlatform` and
store the typed result in a local.

`bAllowRescueUp` / `RescueMaxRise` are **optional** and default off; add them
only if you later choose upward rescue. `AggroRadius` is only used by flyers;
it is harmless to add now but walkers never read it.

### 4.2 Minimum set per milestone

You can add the whole table now, but this is the order that keeps each test
meaningful:

| Milestone | Variables needed |
|---|---|
| Platform ownership + patrol | `HomePlatform`, `PatrolMinX`, `PatrolMaxX`, `GroundZ`, `bStranded`, `bAggro`, `LedgeProbeAhead`, `LedgeProbeDepth`, `MaxPatrolStepZ` |
| Aggro + chase | `ChaseSpeed`, `AggroHalfWidth`, `AggroHalfHeight`, `DeAggroTime`, `UnreachableTime`, `MaxChaseStepZ`, `PlayerGroundProbeDepth`, `bRequireAggroLineOfSight`, `bAggroOnHit` |
| Knockback + rescue | `bWasKnockedBack`, `RescueRadius`, `MinPatrolWidth`, `MaxPatrolWidth`, `MaxDrop` |
| Flyers only | `AggroRadius` |

### 4.3 Movement authority (one loop per asset)

Every child has exactly one movement authority:

| Kind | `bCanMove` | `ChaseSpeed` | Movement code |
|---|---|---|---|
| Walker (Rock, Snail, Slime, Rhino, Wood Log) | `true` | `> 0` if it detects; `0` if it never detects | base `Event Tick` → `PatrolStep` / `ChaseStep`; child never adds a movement Tick |
| Stationary / flyer (Spike Turtle, Ghost, Floating Skull) | `false` | `0` | child's own `Event Tick` / `LaunchCharacter`; base walker loop is skipped |
| Bat | `false` | `300` (used only for `MaxFlySpeed`) | own `Event Tick`; base walker loop is skipped |

`bCanMove` is a **shared-AI gate**, not a `CharacterMovement` property. Setting
it `false` does not stop `Add Movement Input` or `LaunchCharacter`; it stops the
base walker loop. This is how Ghost and Bat keep their own chase without the
base patrol/aggro code also running. Wood Log is the one walker that
temporarily sets `bCanMove=false` while firing; `EndAttack` restores it.

`ChaseSpeed=0` means **never detect or chase**. Snail and Toxic Slime stay in
`PatrolStep`; the base `UpdateAggro` must return to `PatrolStep` before it can
set `bAggro`. This is a data switch, not a per-child Tick.

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

### 5.1 Facing and sprite orientation

Enemy art is drawn facing **left** at sprite yaw 0. Keep `Facing` as the
movement sign (`+1` = `+X`), but map it to the sprite the other way round:

| `Direction` | `Facing` | Sprite yaw | Visual |
|---|---|---|---|
| `>= 0` | `1` | `180` | right |
| `< 0` | `-1` | `0` | left |

`InitEnemy` must call `SetFacing(1.0)`, not just set the `Facing` integer.
Otherwise a freshly spawned walker moves `+X` with the Sprite still at yaw 0
and appears to walk backwards until its first patrol turn.

Ghost is the only child that calls `SetFacing` itself. It currently passes
`-(Player.X - Self.X)` to compensate for the old mapping; with the table above,
remove that `-1` and pass raw `Player.X - Self.X`. Ghost's movement uses
`Normal(Player - Self)`, so this changes only its visual facing.

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

### 6.2 Reachability — acquire vs keep

Two questions, two tests. **Acquire** (start chasing) may use the aggro
rectangle. **Keep** (stay chasing) may not: the rectangle is centred on the
*enemy* and is far narrower than a platform, so a player who runs past
`AggroHalfWidth` is still reachable. Counting that as unreachable made a walker
give up mid-chase after `DeAggroTime` while the player stood on the same
platform (fixed 7 Nov 2026).

```text
Detect = (InBox AND OnHome AND Abs(Player.Z - Self.Z) <= MaxChaseStepZ)
         OR (bAggroOnHit AND Now - LastDamageTime <= DeAggroTime)     # acquire
Keep   = (OnHome AND Abs(Player.Z - Self.Z) <= MaxChaseStepZ)
         OR (bAggroOnHit AND Now - LastDamageTime <= DeAggroTime)     # stay
         OR AggroRadius > 0                                           # flyer
Chase  = Detect OR (bAggro AND Keep)
```

`UnreachableTime` accumulates only on `bAggro AND NOT Keep`, so the de-aggro
clock starts when the player leaves the platform (or drops out of
`MaxChaseStepZ`), never because of the rectangle.

**Box term (acquire)** — the normal detection, all of:

- player is inside the aggro rectangle;
- `IsPlayerOnHomePlatform()` is true;
- `Abs(Player.Z - Self.Z) <= MaxChaseStepZ`;
- optional: a horizontal line trace to the player is clear.

**Hit term** — `bAggroOnHit`, all of:

- `bAggroOnHit` is true (default `false`);
- `Get Game Time in Seconds - LastDamageTime <= DeAggroTime`.

**Gun-aggro set (5 Nov 2026):** `Rock1/2/3`, `Snail`, `WoodLog` and `Bat`. The
walkers use `bAggroOnHit=true`; the base hit term is deliberately cross-platform
and lets `ChaseStep` walk to the ledge (closest safe X) without leaving the
platform. `Bat` must implement the hit branch itself because it replaces the base
walker Tick; `bAggroOnHit` is never read there. Rhino, Ghost, Spike Turtle and
the Skull cannot be gun-aggroed; Toxic Slime cannot be aggroed at all.

In the asset this is `Chase = BooleanOR(Detect, BooleanAND(bAggro, Keep))`: seven
extra nodes pasted from `Scripts/_bp_enemy_base_aggro_keep_paste.txt`
(`AndStay`, `OrStayFly`, `OrKeep`, `AndAggroKeep`, `OrChase`, `Greater`,
`Get AggroRadius`), 54 → **61**. `Scripts/_run_aggro_keep_check.py` proves the
aggro-box pin reaches `Detect` only and that `Keep` is platform + Z (+ hit
window + flyer sphere).

**Pasting it (manual, no Python graph API in 4.27):**

1. Open `BP_EnemyBase` → **`UpdateAggro`** tab.
2. Alt+Click the wire from the `BooleanOR` at `(1632, 176)` into the `Branch` at
   `(1920, 128)` — its **Condition** pin must end up empty (the paste replaces
   it). There are four Branch nodes in this graph; it is the one right of the
   `BooleanOR`, not the `ChaseSpeed <= 0` gate on the far left.
3. Paste `Scripts/_bp_enemy_base_aggro_keep_paste.txt` into the same graph,
   **Compile**, **Save**.
4. `py -3 Scripts/_run_aggro_keep_check.py` must print `RESULT: PASS`
   (`_verify_enemy_base.py` then reports 46/0/0).
5. PIE: aggro a rock, run along the platform past `700` uu — it must keep
   chasing; step off the platform — it must still de-aggro after 2 s.

**After pasting, six wires must be dragged by hand.** The importer only recreates
links between the nodes it creates; every link with a pre-existing endpoint is
dropped (checked 7 Nov 2026: all six new→old links came in empty, all six
new→new links survived). `py -3 Scripts/_run_aggro_keep_check.py` prints exactly
the missing ones as `target.pin <- source.pin   # note`, using the titles and
positions below. By hand (`A` is the upper pin, `B` the lower):

| New node | Pin | Connect to |
|---|---|---|
| `AND` (1104,560) | A | `IsPlayerOnHomePlatform` (672,240) · `Return` — the node with exec pins that feeds the old box `AND` |
| | B | `<=` (1440,544) · `ReturnValue` — `Abs(Player.Z - Self.Z) <= MaxChaseStepZ` |
| `>` (1344,880) | A | `Get AggroRadius` (1104,880) · `AggroRadius`; leave `B` at `0.0` |
| `OR` (1344,640) | A | hit `AND` (1344,-80) · `ReturnValue` — the one whose `A` is `bAggroOnHit`; it was the old `OR`'s `A` |
| | B | `>` (1344,880) · `ReturnValue` |
| `OR` (1568,720) | A | `AND` (1104,560) · `ReturnValue` |
| | B | `OR` (1344,640) · `ReturnValue` |
| `AND` (1792,720) | A | `Get bAggro` (1968,464) · `bAggro` — the getter that feeds the lower `Branch` (2160,336) |
| | B | `OR` (1568,720) · `ReturnValue` |
| `OR` (2032,560) | A | old `OR` (1632,176) · `ReturnValue` — the now-disconnected Detect node |
| | B | `AND` (1792,720) · `ReturnValue` |
| | `ReturnValue` | `Branch` (1920,128) · `Condition` — break the old `OR` wire first (`Alt+Click`) |

None of the seven new nodes has an exec pin, so the Tick flow is unchanged: the
`Branch` still executes from `IsPlayerOnHomePlatform.then`.

The hit term deliberately skips `IsPlayerOnHomePlatform()` and the Z check: the
point is that a walker shot from a platform above walks to the ledge under the
player and waits there instead of forgetting the hit. It reuses `DeAggroTime`
rather than adding a second duration, so one number tunes both clocks; the
consequence is that aggro after a hit lasts up to `2 * DeAggroTime` (about 4 s
at the `2.0` default) — `DeAggroTime` of the window itself, then `DeAggroTime`
again of accumulating `UnreachableTime`. Clear `bAggroOnHit` on a child to get
the pre-change behaviour back with no graph edit.

`LastDamageTime` is stamped by `Event AnyDamage` (`Enemies.md` §4.2) and is
already `-1000.0` at spawn, so a fresh enemy is never pre-aggroed. A hit that
lands during i-frames returns before the stamp and does not refresh the window.

If the player is on another platform, jumping across a gap, or falling into a
pit, the enemy **stands at the ledge** and does not follow.

### 6.3 Aggro loop

```text
Event Tick:
  Branch: bIsDead OR bStranded OR NOT bCanMove -> return
  Branch: bWasKnockedBack -> return
  Branch: ChaseSpeed <= 0 -> PatrolStep(); return   # Snail/Slime: no detection
  Player = Get Player Character(0)
  InBox = IsPlayerInAggroBox(Player)
  Detect = (InBox AND IsPlayerOnHomePlatform(Player)
                 AND Abs(Player.Z - Self.Z) <= MaxChaseStepZ)
            OR (bAggroOnHit AND
                Get Game Time in Seconds - LastDamageTime <= DeAggroTime)
  Keep   = (IsPlayerOnHomePlatform(Player)
                 AND Abs(Player.Z - Self.Z) <= MaxChaseStepZ)
            OR (bAggroOnHit AND
                Get Game Time in Seconds - LastDamageTime <= DeAggroTime)
            OR AggroRadius > 0
  Chase  = Detect OR (bAggro AND Keep)
  Branch: Chase
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

**De-aggro rule:** the clock behind `DeAggroTime` starts only while the player
is **unreachable** — off the enemy's platform, or more than `MaxChaseStepZ`
above/below it. Running along the platform, past the rectangle or not, keeps
`bAggro` and resets `UnreachableTime` every frame. After `DeAggroTime` seconds
unreachable, `bAggro=false` and the enemy resumes patrol from its current
position. If the player returns to a reachable spot, the enemy re-aggros
immediately (`Detect`, and `Keep` alone keeps it aggroed once it is chasing).
`UnreachableTime` also resets while the hit term is what keeps the enemy
chasing, which is why the timer restarts after the window closes.

**Flying aggro has no de-aggro path.** Ghost and Bat never run the de-aggro
branch: they replace the base walker Tick, so `UpdateAggro` is not called at
all. The base rule also carries `AggroRadius > 0` inside `Keep`, so a flyer that
ever does run the walker loop cannot start an `UnreachableTime` clock either —
a sphere has no platform edge to lose the player over.


### 6.4 Suggested defaults

| Enemy | Detection | Width / radius | Height | De-aggro | Chase |
|---|---|---|---|---|---|
| Rock1/2/3 | rectangle | `700` | `500` | `2.0 s` | yes |
| Rhino | rectangle | `1200` | `500` | `2.0 s` | yes (charge) |
| Wood Log | rectangle | `1400` | `500` | `2.0 s` | no — stops to shoot |
| Ghost | sphere | `550` | — | **never** | yes, through walls |
| Bat | sphere `1000` + hit branch (staged) | — | — | **never** | yes, collides |
| Snail | hit only | — | — | `2.0 s` | yes, after a hit (`250`) |
| Toxic Slime | none | — | — | — | no |
| Spike Turtle | none | — | — | — | no |
| Floating Skull | none | — | — | — | no |

The `500` height is intentional: it covers the player's jump/double-jump. It
does **not** cause cross-platform aggro because `IsPlayerOnHomePlatform()` is
part of the acquire test. It also does not *end* a chase: once `bAggro` is set,
only the platform + `MaxChaseStepZ` pair (the `Keep` term) can start the
de-aggro clock, so the rectangle width is purely a "how far away do I notice
you" number. Tune the width/speed after PIE.

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

`LaunchCharacter` is `ACharacter::LaunchCharacter`. With `bZOverride=false` it
adds the victim's **current** Z velocity to the vector, so a `KnockbackForce`
of `0` still produces a non-zero `PendingLaunchVelocity`.
`UCharacterMovementComponent::HandlePendingLaunch()` then runs
`SetMovementMode(MOVE_Falling)`. For a walker that is the intended arc; for a
flyer it is a trap — `GetMaxSpeed()` returns `MaxWalkSpeed`, which the block
above just set to `MoveSpeed`, and `GetFallingLateralAcceleration()` drops Z and
scales by `AirControl` (`0.05`). Use `bZOverride = true`: a zero force then sends
a zero vector, `HandlePendingLaunch()` returns early and `MOVE_Flying` /
`MaxFlySpeed` survive. `Enemies.md` §4.2 and §6.8 have the Bat case.

**The vertical component is the knockback (7 Nov 2026).** With the pin forced to
`true`, a launch of `(F, 0, 0)` has no arc at all, so the victim re-grounds on the
next move and `ApplyVelocityBraking` removes everything above `MaxWalkSpeed` at
`GroundFriction^2 * BrakingDecelerationWalking` = `8^2 * 2048` = `131072` uu/s² —
about 15 uu of travel for any `F`. `AnyDamage` therefore feeds `MakeVector.Z`
with `KnockbackForce * 0.4`: the victim stays in `MOVE_Falling` (no ground
friction, and Tick is gated by `bWasKnockedBack`) for
`2 * Lift / (980 * GravityScale)` and covers `KnockbackForce * t_air`. With the
live `KnockbackForce = 1200` and `GravityScale = 3` that is `Lift 480`,
`0.327 s`, ~392 uu. `BP_Bat` keeps `KnockbackForce = 0`, so both components stay
zero and the flyer is untouched. The link is in the asset (pasted from
`Scripts/_bp_enemy_base_knockback_lift_paste.txt`, compiled and saved):
`py -3 Scripts/_run_knockback_lift_check.py` prints `RESULT: PASS` with
`lift=480 uu`, `air=0.327 s`, `shove=392 uu`.

`Set bAggro = false` clears the current chase but not the hit window:
`LastDamageTime` was stamped a few nodes earlier, so once `bWasKnockedBack`
clears the walker re-aggros for the remaining `DeAggroTime` (§6.2). That is
intended — a knocked-back walker comes back for the player instead of
forgetting the hit.

Do not clear `bWasKnockedBack` with a single fixed timer. A character can be in
the air for a variable time, and a purely horizontal hit may **not leave the
floor at all** — in that case `Event On Landed` never fires and the enemy would
stay frozen. Resolve it in two places:

- `Event On Landed` -> `ResolveKnockback`;
- `Event Tick`: if `bWasKnockedBack` and `CharacterMovement.IsFalling()` is
  false, call `ResolveKnockback` immediately (the hit stayed on the floor).

In the UE graph the landing node is **`Event On Landed`** (the `OnLanded`
BlueprintImplementableEvent inherited from `ACharacter`), not `Event Landed`.
It exposes the `Hit` result and has **no Return Node**: an event graph ends at an
unconnected exec pin. Return Nodes belong only in function graphs.

`ResolveKnockback` is the body in §7.2 (clear flag, find/adopt platform).

### 7.2 Landing

`ResolveKnockback` (called by `Event On Landed` **and** by the Tick fallback in
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
  Branch: Delta.Z < 50           # Delta = Platform.Location - Self.Location
                                 # same as Platform.Z < Self.Z + 50
  Keep nearest valid Candidate
Branch: Candidate valid
  True  -> SetActorLocation(Candidate.Location + (0,0,120),
                            bSweep=false, bTeleport=true)
           Set Movement Mode (Falling)
           # gravity drops it onto a guaranteed broad platform
           # Event On Landed runs FindHomePlatform again and adopts it
  False -> stay stranded (idle); no suicide drop
```

The teleport/drop is deliberate: the destination is an authored zone, so it
cannot be a hole or a 100 uu step. A short `Set Actor Hidden In Game` or a dust
puff can hide the reposition later. Do not trace blindly downward and walk off;
that is how enemies kill themselves.

`Delta` is the vector difference between the platform location and Self location.
Break it once; `Delta.Z < 50` is the same height test as
`Platform.Z < Self.Z + 50` and reuses the X/Z values used for the distance.

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
| `BP_Bat` | hang, then fly | sphere `1000`, no de-aggro | `1` only after trigger | `2` | collides with wall/floor |
| `BP_WoodLog` | patrol; stops to shoot | rectangle `1400×500`, de-aggro `2 s` | `1` | `3` | horizontal shots only |
| `BP_PeaPlant` | unused | — | — | — | keep out of build order |

### 8.1 Spike Turtle

- `bCanMove=false`, `ChaseSpeed=0`; no patrol Tick and no detection.
- `bUseHealth=false`, `bInvulnerable=true` permanently.
- `SpikeCycle`/`FinishSpikeChange` remain, but `FinishSpikeChange` sets
  `bDealContactDamage = bSpikesOut` and `ContactDamage = 1.0` (never `2.0`).
- Player bullets and `Kill` are no-ops. A `BP_KillVolume` below the arena
  destroys it by tag if it falls.
- It is an environmental hazard: sometimes dangerous, never a chase target.

### 8.2 Rocks

- Add the rectangle aggro/de-aggro loop from §6.
- Set `bAggroOnHit=true` on all three tiers (A2's CDOs): the rectangle is
  `700` wide, so a hit from outside it would otherwise be forgotten instantly.
  **DONE 5 Nov 2026:** live and verified on all three CDOs.
- `MoveSpeed`/`ChaseSpeed` per tier; keep the existing `100 / 140 / 180`
  identities and use `120 / 160 / 200` for chase as a starting point. Tune
  separately after PIE.
- Split pieces are spawned with `LaunchCharacter`; each piece runs `Event On Landed` and
  adopts the platform it lands on (or becomes stranded/rescued). Do not assume
  the parent's `HomePlatform` is still valid.

### 8.3 Snail

- `ChaseSpeed=250` with **both aggro halves `0`** and `bAggroOnHit=true`: the
  zero box means it never detects on its own, the hit window
  (`EnemyAI.md` §6.2) means a bullet wakes it for `DeAggroTime`. `ChaseSpeed=0`
  would swallow the hit too — the gate returns to `PatrolStep` before the box.
  Raised from `80` on 7 Nov 2026: `UpdateAggro`'s chase branch writes
  `MaxWalkSpeed = ChaseSpeed`, and `80` uu/s against the player's `1000` uu/s
  looked like standing still.
- Keep the normal patrol and the shell death override.
- Both the body and the shell use the base `PatrolStep` + `LedgeAhead`; do not
  add a second shell Tick. The shell must sweep the platform, not fall off it.
- `ShellContactDamage` must be `1.0`, not `2.0`.
- Shell remains invulnerable and self-destructs after `ShellLifetime`.

### 8.4 Ghost

- Set `bCanMove=false`, `ChaseSpeed=0`; use the inherited `bAggro` and
  `AggroRadius`. The Ghost's own Tick is the only movement authority.
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

- Set `ChaseSpeed=0`; no detection and no chase.
- Keep the patrol and puddle timer.
- Add the ledge guard; it must not walk onto a lower step or into a pit.
- Contact `1`. Puddle kill unchanged; puddles are player-only.

### 8.6 Rhino

- Replace the old invulnerable wall-kill. New contract:
  - `MaxHealth=4`, `CurrentHealth=4`, `bUseHealth=true`;
  - `bInvulnerable=true` so player bullets and `Kill` are ignored;
  - `WallHitCooldown=0.5`, `LastWallHitTime=-1000`.
- Movement: inherited `MoveSpeed=120`, `ChaseSpeed=600`; `ChargeSpeed=600`.
  Override `UpdateAggro`, call `Parent: UpdateAggro`, then set
  `bCharging=bAggro`. Do not duplicate detection.
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

- Set `bCanMove=false`, `ChaseSpeed=0`; the base walker loop is skipped. The
  `LaunchCharacter` bounce and `Event Hit` are its only movement.
- Keep the ON/OFF toggle and `Event Hit` reflection.
- `BounceSpeed` is now a **slow** bounce: `≈300` (bullet speed is `900`).
  Keep the Z component of the reflection; do not add gravity.
- No detection, no chase. Contact only when ON; `1` damage.
- If it falls into a pit, `BP_KillVolume` removes it.

### 8.8 Bat

- Set `bCanMove=false`; use the inherited `ChaseSpeed=1000`. The Bat's own Tick
  is the only movement authority.
- Trigger sphere is `1000` (was `800`; `600` was the first playtest value). The
  wider sphere covers the approach from the playable floor; it still only
  starts the chase when the player is inside it.
- `KnockbackForce=0` for the Bat, so a hit cannot slide it along the ceiling or
  push it out of the trigger. **`KnockbackForce=0` alone is not enough** (found
  7 Nov 2026): with the base's `bZOverride=false` the launch vector still carries
  the Bat's own Z velocity, and `HandlePendingLaunch()` forces `MOVE_Falling`,
  where `GetMaxSpeed()` returns `MaxWalkSpeed = MoveSpeed = 100` and only
  `AirControl`-scaled X/Y input applies. Fix the base pin
  (`LaunchCharacter.bZOverride = true`) or give the Bat a Tick guard that
  re-asserts `SetMovementMode(Flying)` — see `Enemies.md` §4.2 and §6.8 and
  `Scripts/_check_bat_hit_knockback.py`.
- A non-lethal hit is meant to force aggro: the `RefreshStateFlipbook` branch
  checks `bWasKnockedBack`, clears the flag, sets
  `bTriggered`/`bChasing`/`bDealContactDamage`, **sets
  `CharacterMovement.MaxFlySpeed = ChaseSpeed`**, then calls the parent. The
  full staged patch additionally clears the pending `HangIdle` timer.
  `bAggroOnHit` is walker-only and is
  never read here. All three issues are verified fixed in PIE: the live asset
  has the 13-node hit branch plus the `MaxFlySpeed` write, and the EventGraph
  `HangIdle` custom event is gated on `bTriggered`. The full 17-node
  replacement remains staged in `Scripts/_bp_bat_refresh_modified_v2.txt` for a
  clean re-paste. Without the speed write, a hit before `StartChase` leaves the
  Bat at the flying default `400` instead of `1000`.
- `CharacterMovement.MaxAcceleration=8192` so that after a hit or the
  `StartChase` transition it reaches `MaxFlySpeed` immediately instead of
  drifting slowly.
- The `BeginPlay` `HangIdle` timer is `0.6 s`, but `StartChase` is started after
  `0.5 s`. The live fix gates the EventGraph `HangIdle` custom event on
  `bTriggered` (optionally `bTriggered OR bIsDead`): once the Bat is triggered,
  return instead of playing `HangingFlipbook`. That covers both the normal
  trigger and the hit path without relying on timer order. Alternative: shorten
  the `HangIdle` delay to `0.3 s` and call `K2_ClearTimer("HangIdle")` on the hit
  chain.
- After the `CeilingOut` animation, `bChasing=true` and it chases directly in
  the X/Z plane. Unlike Ghost, it **collides with walls and floors**: do not set
  `WorldStatic = Ignore`. If it hits a wall, it stops/slides; there is no
  pathfinding.
- No de-aggro. Contact `1` only after the trigger.
- It is a normal health enemy (`2`) and can be shot down.

### 8.9 Wood Log

- Override `ChaseStep` to stand: no `Add Movement Input` while aggroed.
  `TryFire` sets `bCanShoot=false` and `bCanMove=false`; `EndAttack` restores
  both.
- Replace unlimited-range fire with the rectangle detection in §6:
  `1400×500`, same platform, `DeAggroTime=2.0`.
- It **stops and shoots** while aggro; it does not chase around the platform.
  `TryFire` is gated by `bAggro`, not by "player exists anywhere".
- Set `bAggroOnHit=true` (A2's CDO) so a hit from outside the `1400×500`
  rectangle still turns it. It needs `ChaseSpeed > 0` (the gate above), and the
  `ChaseStep` override keeps it planted, so the flag buys aim, not movement.
  **DONE 5 Nov 2026:** live and verified on `BP_WoodLog`.
- It only fires horizontally: projectile direction `(Facing,0,0)`, muzzle Z
  fixed by `MuzzleOffset.Z`. Do not aim at the player's Z.
- If the player leaves the platform / becomes unreachable for `DeAggroTime`,
  `bAggro=false`, `EndAttack`, resume patrol (the rectangle itself is
  acquire-only, `§6.2`). If the player re-enters while reachable, re-aggro.
- No vertical aim means a jumping player can dodge; that is intended.
- Contact `1`; health `3`.


---

## 9. Contact damage: why the capsule alone was not enough

**Fixed 24 Oct 2026:** option A is implemented — `ContactBox` is compiled with
`QueryOnly`, `Pawn = Overlap`, all other channels `Ignore`, and the existing
contact chain is bound to its component-overlap event. The base verifier reports
**45 PASS / 0 FAIL**. The finding below is kept as the rationale.

**Fixed 25 Oct 2026 — capsule is now non-solid.** All four enemy classes compile
with `CollisionCylinder → Pawn = Overlap`; `WorldStatic`/`WorldDynamic` remain
`Block`. `py -3 Scripts\_inspect_enemy_contact.py` now reports
**4 PASS / 0 FAIL**. The player falls through the enemy and the existing
`ContactBox` catches contact a few units lower, so the enemy no longer acts as a
platform. The numbers below are the measurement that led to the fix.

**2026-10-25 runtime finding.** The live `ContactBox` is `74.96 uu` tall and
centred on the capsule. The live child capsules are taller: `BP_Rock1` has
`CapsuleHalfHeight = 106.25`, `BP_Snail` `75.0`, and `BP_RockBase` `81.25`. The
top of the capsule was therefore outside the trigger. A player landing on the
then-solid capsule stood on the enemy, slid down the rounded top, and only
triggered `Kill` from the side. The capsule was also `Pawn = Block`, so it
blocked the fall. The fix was:

1. `CollisionCylinder` → `Pawn = Overlap` (keep `WorldStatic`/`WorldDynamic =
   Block`). This is the required fix. The player falls through the enemy and the
   existing ContactBox catches the contact instead of the enemy acting as a
   platform. A top gap remains on `BP_Rock1` (31.29 uu), but it is harmless now:
   the player falls into the box rather than standing on the capsule.
2. Only if you deliberately keep the capsule solid: give **each child** a
   ContactBox that covers that child's full capsule height. Do **not** simply
   scale the shared base box to `Z=120`; that extends 45 uu below a Snail and can
   kill a player walking under a thin platform.

Run `py -3 Scripts\_inspect_enemy_contact.py` to verify all four enemy classes:
it must print `SUMMARY 4 PASS / 0 FAIL`.

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

**Current position (5 Nov 2026): steps 0–2 are code-complete; step 2's remaining
gate is PIE.** The base has all 13/13 AI functions and 25/25 §4 variables with
the documented defaults (`_check_enemy_ai_vars.py`: 25 PASS). The aggro-on-hit
change is in `UpdateAggro` (54 nodes; the three corrected links are asserted by
`_verify_enemy_base.py`, which is now **45 PASS / 0 FAIL**). The Snail's aggro
CDO is set (`ChaseSpeed=250`, zero box, `bAggroOnHit=true`); its health/movement/
flipbook defaults remain. The next task is PIE tests 1–9 and the `M1 GREEN` line.
Do not start a **walker** child (`Snail`, `Rocks`, `Slime`, `Rhino`, final
`WoodLog` aggro) until that line exists. Stationary/flyer children (`SpikeTurtle`,
`Ghost`, `Bat`, `FloatingSkull`) and the projectile/puddle/shooter support may be
built in parallel because they do not read the walker AI. See
`Docs/EnemyWorkPlan.md` for the owner split and M1 gate.

0. **DONE — contact fix.** `ContactBox` is compiled and the
   `On Component Begin Overlap` chain is verified: **45 PASS / 0 FAIL**.
   Re-run `py -3 Scripts\_verify_enemy_base.py` if the base is edited.
1. **DONE — `BP_EnemyPlatform` marker + auto-placement.** Seven auto zones
   exist in `L_Level_01`. `bEnable` was renamed to `bEnabled` on 24 Oct 2026;
   live check: `bEnabled=true`, `Zone` is a `BoxComponent`
   (`extent 50,50,20`, `NoCollision`, hidden), `PatrolInset=80`.
2. **DONE — `BP_EnemyBase` AI core (13/13 functions).** All platform/patrol,
   aggro/chase and rescue functions are built; all 25 §4 variables are in with
   the documented defaults. The aggro-on-hit `BooleanOR` is wired and verified.
   1. **DONE** — `PointInPlatformZone`, `PointInPlatformXZ`,
      `FindHomePlatform`, `AdoptPlatform` (home ownership).
   2. **DONE** — `LedgeAhead`, `PatrolStep` (edge-safe patrol).
   3. **DONE** — `IsPlayerOnHomePlatform`, `IsPlayerInAggroBox`, `ChaseStep`,
      `UpdateAggro` (rectangle + de-aggro + post-hit window).
   4. **DONE** — `ResolveKnockback`, `MeasurePlatformWidth`, `TryRescue`
      (landing, stranded, stairs).
   5. **DONE** — `BeginPlay` → `FindHomePlatform`, `Event On Landed` →
      `ResolveKnockback`, `Tick` → the state loop, and `bWasKnockedBack` is set
      in `AnyDamage` before `LaunchCharacter`.
   **NEXT** — run PIE tests 1–9 and post `M1 GREEN`.
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
- **Contact overlap is fixed (24 Oct 2026).** `BP_EnemyBase` has a compiled
  `ContactBox` (`QueryOnly`, `Pawn = Overlap`, everything else `Ignore`) and the
  component-overlap chain. `Scripts\_verify_enemy_base.py` reports **45 PASS /
  0 FAIL**; keep that chain intact while adding the AI nodes.
- **All numbers are starting points.** PIE-tune after the first placement.

