# BP_Trap_Saw_New - configurable saw trap - build guide

**Status (15 Nov 2026):** built and **verified in PIE**. The saw sweeps
between two draggable `Scene Components` (`SweepStart` / `SweepEnd`) using a
triangle wave computed in `Event Tick`; one leg takes `TransitionDuration`
seconds, it reverses forever when `bPingPong` is on, and it never moves at all
when `bMovable` is off.

Activation does **not** move the blade. `ActivateSaw` projects the blade's own
position onto the rail, starts `SweepProgress` at that phase, and lets the tick
take over, so a saw placed anywhere on (or beside) the rail slides away from
where the designer put it. `bSweepTowardEnd` picks which way the first leg
goes. The activation snap that produced the "teleports to `SweepStart`" bug is
deleted; the only code that writes `TrapRoot`'s location is the tick's `VLerp`.

The two older defects are closed:

- the transform no longer snaps - the activation snap is gone, and the position
  is always `VLerp(StartLocation, TargetLocation, alpha)`;
- the blade spins - `Sprite -> Play` is called once in `ActivateSaw`, after
  `Stop` + `Set Playback Position(0)` (the call that used to live in
  `FinishSawMorph`).

The morph path (`SawTick_Morph`, `FinishSawMorph`, `MorphElapsed`,
`MorphAlpha`, `bTransitioning`) still exists in the asset but is **dead code**:
`bTransitioning` is set to `false` by `ActivateSaw` and never set back to
`true`, so the tick never enters it. The spline path, `BP_Chain`, the chain
material and `TargetOffset` were dropped; the chase mode is retired in favour
of the rail sweep, and `bChasePlayer` is left in the asset unused.

**Final verification:** the PIE probe (`Scripts/_probe_saw_speed.py`) sampled
`TrapRoot` every tick and showed a monotonic glide between the two gizmos with no
per-frame reversals, and the reveal was checked by eye: the blade stays put on
activation and then starts sliding. The earlier failure mode (reversals every
~10 ms) is what proved the morph composite was broken.

UE 4.27 Python can create the Blueprint asset and set its parent class, but this
build exposes **no** component/variable/K2-node creation API. The graphs are
hand work; the export scripts below are read-only diagnostics.

**Quick start:** sections 6 and 7 are the per-instance recipes and the PIE
checklist. Section 5 has the exact graph.

---

## 1. What this trap is

One Blueprint for every saw instance. The same class covers:

- a normal, always-visible saw obstacle;
- a visible **saw-off** prop that turns on / grows when the player walks near
  (the "sawoff" surprise);
- a hidden trap that is invisible until the player enters its reveal volume;
- a **rail saw** that sweeps back and forth between two designer-placed points;
- a **one-way pass** saw that crosses once per cycle and wraps.

The important design split is **visibility is not activation timing**:

```
bStartHidden            = can the player see it before activation?
bActivateOnPlayerNear   = do we wait for the player, or activate at BeginPlay?
bMovable                = may its location change?
bPingPong               = while movable, reverse at the ends (true) or wrap (false)
bSweepTowardEnd         = first leg heads to SweepEnd (true) or SweepStart (false)
```

That gives these useful combinations:

| `bStartHidden` | `bActivateOnPlayerNear` | Result |
|---|---|---|
| `false` | `false` | Normal obstacle: visible, spinning, lethal from BeginPlay. |
| `false` | `true` | Visible saw-off prop: the player sees the still blade; entering `RevealBox` activates it - it starts spinning and, if movable, slides away. |
| `true` | `true` | Hidden trap: invisible and harmless until the player enters `RevealBox`; then it appears and sweeps. |
| `true` | `false` | Hidden at spawn but activates immediately. Rarely useful; kept so the two switches stay independent. |

And the movement modes:

| Intent | Settings |
|---|---|
| Static obstacle | `bMovable = false` |
| Static, revealed | `bMovable = false`, `bActivateOnPlayerNear = true` |
| Rail saw (the default design) | `bMovable = true`, `bPingPong = true`, `SweepStart`/`SweepEnd` apart |
| One-way pass | `bMovable = true`, `bPingPong = false` (wraps at the end) |
| Legacy homing saw | `bMovable = true`, `bChasePlayer = true` - unused, unsupported; see 5.6 |

A sweep is defined by **two gizmos, not by a number**. The designer drags
`SweepStart` and `SweepEnd` in the level viewport per placed instance, so the
same Blueprint can sweep horizontally along a floor, vertically up a shaft, or
along any diagonal without touching defaults.

The placed actor is **where the blade rests**, not necessarily an endpoint. A
saw parked in the middle of the rail starts its first leg from that spot; a saw
parked on a gizmo starts from that end. Nothing moves at activation.

**Damage rule:** this is an ordinary trap. It inherits `BP_TrapBase`'s
`Trigger` overlap, which is already gated by
`Equal(OtherActor, Get Player Character(0))` and calls `Kill` on the player
only. Do **not** add a second `Kill` or `Apply Damage` to the child. Enemies and
bullets must not trigger or damage it (`Docs/TrapTriggers.md` section 2).

Because `Trigger` is a child of `TrapRoot`, it travels and scales with the
blade: a sweeping saw kills anywhere along its line, not just at the point
where the actor was placed.

---

## 2. Art facts (verified)

| Fact | Value |
|---|---|
| Spinning art | `FLB_Saw`, 8 frames, 14 fps, frame size 38x38 px |
| Still / off art | `SPR_SawOff`, 38x38 px |
| Pixels per unreal unit | `0.16` |
| Natural blade size | `38 / 0.16 = 237.5` uu |
| One-tile scale | `100 / 237.5 = 0.4211` |
| Off frame | **`FLB_Saw` frame 0 is pixel-identical to `SPR_SawOff`** |

The last row means there is **one** visual component. Do not add a second
PaperSpriteComponent for `SPR_SawOff`. The still blade is frame 0 of the same
flipbook.

The `Sprite` pivot is `TOP_LEFT`. To centre a one-tile blade on the actor
origin, put the inherited `Sprite` at relative location `(-50, 0, 50)` and
scale it to `0.4211`. The trigger then sits at the actor origin.

Half the blade is meant to be hidden behind the ground: place the sweep line so
the bottom of the sprite is inside the floor tile. That is the "saw poking out
of the floor" look; no extra art is needed.

---

## 3. Components (hand work)

### 3.1 One-time pivot in `BP_TrapBase`

**Do not rename, delete or replace `DefaultSceneRoot`.** It is inherited from
`BP_TrapBase` and is the actor root for every trap. UE 4.27 also refuses to
reparent inherited components in a child Blueprint:
`FSCSEditorTreeNodeComponentBase::CanReparent()` returns false for inherited
nodes and for the default root. Dragging inherited `Sprite`/`Trigger` in
`BP_Trap_Saw_New` therefore cannot work.

If you already added `TrapRoot` in the child, delete that local component first.
It cannot parent inherited components and would collide with the inherited
name.

Create the pivot once in the parent, where `Sprite` and `Trigger` are local:

1. Open `Content/DontTrustTheLevels/Traps/Blueprints/BP_TrapBase`.
2. Components -> **+ Add** -> **Scene Component**, rename it **`TrapRoot`**.
   It stays a child of `DefaultSceneRoot`; leave its relative transform at
   `(0,0,0)`, scale `1`.
3. Drag **`Sprite`** onto **`TrapRoot`**, then drag **`Trigger`** onto
   **`TrapRoot`**. These components are local to `BP_TrapBase`, so the editor
   allows the reparent.
4. Compile and save `BP_TrapBase`.
5. Open `BP_Trap_Saw_New`; `TrapRoot` is now inherited, and `Sprite`/`Trigger`
   are already under it. Do not add a second `TrapRoot`, and do not try to
   reparent inherited components in the child.
6. In `BP_Trap_Saw_New`, add the local components:
   **+ Add** -> **Box Collision**, rename it **`RevealBox`**;
   **+ Add** -> **Scene Component**, rename it **`SweepStart`**;
   **+ Add** -> **Scene Component**, rename it **`SweepEnd`**.

All three local components must be children of **`DefaultSceneRoot`**, **never**
of `TrapRoot`:

- `RevealBox` is a proximity sensor, so it should not scale or move with the
  blade.
- `SweepStart` / `SweepEnd` **define** the motion; parenting them to the thing
  they move would make the endpoints chase the blade and the sweep degenerate.

This is a shared base-class change: `BP_Trap_Spikes` and `BP_Trap_FallPlat`
inherit the new identity pivot too. Their relative transforms are unchanged,
but PIE one instance of each after the edit.

`TrapRoot` is the single animation pivot: moving or scaling it moves/scales the
blade and the lethal trigger together. `RevealBox`, `SweepStart` and `SweepEnd`
stay at the original actor position.

### 3.2 Exact component settings

**Set the `Sprite`/`Trigger` rows in `BP_Trap_Saw_New`, not in `BP_TrapBase`.**
They are inherited overrides; changing them in the parent would also change
`BP_Trap_Spikes` and `BP_Trap_FallPlat`. In `BP_TrapBase`, the only change is
the identity `TrapRoot` pivot and the two attachment links.

| Component | Parent | Relative location | Relative scale | Key settings |
|---|---|---|---|---|
| `DefaultSceneRoot` | - | `(0,0,0)` | `(1,1,1)` | - |
| `TrapRoot` | `DefaultSceneRoot` | `(0,0,0)` | `(1,1,1)` | - |
| `Sprite` | `TrapRoot` | `(-50, 0, 50)` | `(0.4211, 0.4211, 0.4211)` | Flipbook = **`FLB_Saw`**; **Looping = on**; Collision Presets = **`NoCollision`** |
| `Trigger` | `TrapRoot` | `(0, 0, 0)` | `(1,1,1)` | Collision Presets = **`OverlapAllDynamic`**; Generate Overlap Events = **on**; Box Extent = `(50, 50, 50)` |
| `RevealBox` | `DefaultSceneRoot` | `(0, 0, 0)` | `(1,1,1)` | Collision Presets = **`OverlapAllDynamic`**; Collision Enabled = **Query Only**; Generate Overlap Events = **on**; Box Extent = `(300, 100, 300)` (tune per instance) |
| `SweepStart` | `DefaultSceneRoot` | per instance | `(1,1,1)` | Scene Component; **movable gizmo**, no collision |
| `SweepEnd` | `DefaultSceneRoot` | per instance | `(1,1,1)` | Scene Component; **movable gizmo**, no collision |
| `BillboardComponent_1` | inherited | - | - | editor icon only; leave alone |

**Why `Sprite` is `NoCollision`:** the blade is a visual, not a solid platform.
The inherited `Trigger` is the lethal volume. This also keeps enemies
trap-neutral, exactly like `BP_Trap_Spikes.Sprite`.

If the `Sprite` component exposes **Play Automatically**, turn it **off** only
if you also call `Sprite -> Play` yourself after activation. Leaving it on is
what the current build does and the result was accepted in PIE; do not change
it without re-testing the blade animation.

**Why `Trigger` is `(50,50,50)`:** with `TrapRoot` scale 1 the box is a
100x100x100 uu volume around the one-tile blade. Scaling `TrapRoot` to
`TargetScale = 2` scales the box to 200 uu, so the hitbox always matches the
new blade size.

**RevealBox extent is per instance.** `(300, 100, 300)` means a 600x200x600 uu
proximity volume around the saw. For a floor trap that should only fire when
the player is almost on it, use `(150, 100, 150)`. For a tall jump-catching
trap, raise Z (for example `(250, 100, 350)`). Keep `RevealBox` off the
`PlayerStart`; an actor spawned already overlapping the player is an
initialization edge case.

**Compile** `BP_TrapBase` after the pivot, then compile `BP_Trap_Saw_New` after
adding the local components and the variables. Click the inherited `TrapRoot`
component and confirm its relative transform is still `(0,0,0)` with scale `1`.

---

## 4. Variables (hand work)

My Blueprint -> **Variables**. Set the type in Details, tick **Instance
Editable** where noted, then **Compile** before wiring anything.

| # | Name | Type | Default | Instance Editable | Meaning |
|---|---|---|---|---|---|
| 1 | `bStartHidden` | Boolean | `false` | yes | If true the blade is invisible before activation. |
| 2 | `bActivateOnPlayerNear` | Boolean | `false` | yes | If true, wait for the player to enter `RevealBox`; if false, activate at BeginPlay. |
| 3 | `bMovable` | Boolean | `false` | yes | If false the saw never moves (static obstacle). If true it sweeps between `SweepStart` and `SweepEnd`. |
| 4 | `bPingPong` | Boolean | `true` | yes | While movable: true = reverse at each end; false = one-way pass that wraps. |
| 5 | `bSweepTowardEnd` | Boolean | `true` | yes | First leg heads toward `SweepEnd` (true) or `SweepStart` (false). Only the first leg - after that the triangle decides. |
| 6 | `bChasePlayer` | Boolean | `false` | yes | **Legacy, unused.** Chase mode is retired; leave it false. |
| 7 | `StartScale` | Float | `1.0` | yes | Origin size. `1.0` is a one-tile / 100 uu blade. |
| 8 | `TargetScale` | Float | `1.0` | yes | End size. `2.0` is two tiles / 200 uu. Keep equal to `StartScale` for a pure move. |
| 9 | `TransitionDuration` | Float | `2.0` | yes | **Seconds per leg** of the sweep. Clamped to `0.01` in the tick, so `0` means "as fast as the framerate". |
| 10 | `ChaseSpeed` | Float | `300.0` | yes | **Legacy, unused** (only read by `ChaseStep`). |
| 11 | `TargetOffset` | Vector | `(0,0,0)` | yes | **Legacy, unused.** Replaced by `SweepEnd`. |
| 12 | `SweepProgress` | Float | `0.0` | no | Internal sweep clock, 0..2. `0` = at `SweepStart`, `1` = at `SweepEnd`, `2` = back. Seeded at activation from the blade's position on the rail. |
| 13 | `bActive` | Boolean | `false` | no | Internal. Set true once, at activation. |
| 14 | `bTransitioning` | Boolean | `false` | no | **Legacy.** Kept at `false`; the morph lane never runs. |
| 15 | `MorphElapsed` | Float | `0.0` | no | **Legacy**, unused. |
| 16 | `MorphAlpha` | Float | `0.0` | no | **Legacy**, unused. |
| 17 | `StartLocation` | Vector | `(0,0,0)` | no | Internal. `TrapRoot` position when static, `SweepStart` when movable. |
| 18 | `TargetLocation` | Vector | `(0,0,0)` | no | Internal. Always `SweepEnd`. |
| 19 | `StartScale3D` | Vector | `(1,1,1)` | no | Internal. Captured from `TrapRoot` at activation. |
| 20 | `TargetScale3D` | Vector | `(1,1,1)` | no | Internal. `Make Vector(TargetScale,TargetScale,TargetScale)`. |

Deleting the legacy rows (6, 10, 11, 14, 15, 16) is safe once `ChaseStep`,
`FinishSawMorph` and the `SawTick_Morph` composite are gone. Leaving them costs
nothing but confusion.

---

## 5. Graph (hand work)

Functions in **My Blueprint -> Functions**:

- `ActivateSaw` - no inputs, no outputs. The one entry point.
- `FinishSawMorph` - **legacy**, no longer called from `ActivateSaw`.
- `ChaseStep` - **legacy**, unreachable.

Keep the Event Graph for `BeginPlay`, the `RevealBox` overlap and `Tick`.

> **Polarity warning.** Several branches below have a "do nothing" or
> "wait" side. Read each True/False label twice before compiling. This project
> has already lost time to a correct class check with its exec pins reversed
> (`Docs/DashDamage.md`). The common reversals here are:
>
> - `bActive` **True = return**, False = activate.
> - `bStartHidden` **True = invisible / Trigger NoCollision**.
> - `bActivateOnPlayerNear` **True = arm RevealBox**, False = activate now.
> - `bMovable` **True = sweep**, False = static.
> - `bPingPong` **True = reverse at the ends**, False = wrap.
> - `Select` node **Option 1 is the true side**; the `Select Float`
>   **function** is the opposite - `bPickA` true returns **A**.
> - `bMovable ✔` must give `StartLocation = SweepStart` and
>   `TargetLocation = SweepEnd`.

### 5.1 `ActivateSaw` function

```
Function Entry (ActivateSaw)
  -> Branch (Condition = GET bActive)
       True  -> (leave the True pin empty - already active)
       False -> SET bActive = true
                Sprite -> Set Visibility
                    New Visibility = true
                    Propagate to Children = true
                Trigger -> Set Collision Enabled
                    New Type = QueryOnly
                RevealBox -> Set Collision Enabled
                    New Type = NoCollision
                Sprite -> Play
                SET StartLocation = Select (Vector)
                    Index    = GET bMovable
                    Option 0 = TrapRoot -> Get Relative Location     (static: stay put)
                    Option 1 = SweepStart -> Get Relative Location  (movable: line start)
                SET StartScale3D = TrapRoot -> Get Relative Scale 3D
                TrapRoot -> Set Relative Scale 3D
                    New Scale 3D = StartScale3D
                SET TargetLocation = SweepEnd -> Get Relative Location
                SET TargetScale3D = Make Vector
                    X = GET TargetScale
                    Y = GET TargetScale
                    Z = GET TargetScale
                SET SweepProgress = <rail phase of the blade>   (see below)
                SET bTransitioning = false
```

**There is no snap.** Nothing in `ActivateSaw` writes `TrapRoot`'s **location**;
the first tick after activation places the blade on the rail at the phase
`SweepProgress` already holds, which is the blade's own spot. That is what makes
a mid-rail placement safe. (The function does reset `TrapRoot`'s **scale** to
`StartScale3D`, which is a no-op while the blade keeps its BeginPlay size.)

**Seeding `SweepProgress` (pure math, no exec):**

```
Seg  = SweepEnd.RelativeLocation  - SweepStart.RelativeLocation     (Vector)
Off  = TrapRoot.RelativeLocation   - SweepStart.RelativeLocation     (Vector)
Num  = DotProduct(Off, Seg)
Den  = DotProduct(Seg, Seg)
Safe = Max(Den, 0.01)                       // guards a zero-length rail
Raw  = Num / Safe
A0   = Clamp(Raw, 0.0, 1.0)                 // 0 = SweepStart, 1 = SweepEnd
Back = 2.0 - A0                             // same alpha, on the return leg
Prog = Select Float(A = A0, B = Back, bPickA = GET bSweepTowardEnd)
SET SweepProgress = Prog
```

`Select Float` is the **math function** (pins `A`, `B`, `bPickA`), not the
`Select` node: `bPickA = true` returns **`A`**. So `A = A0` (alpha rises ->
toward `SweepEnd`) and `B = 2 - A0` (alpha falls -> toward `SweepStart`).

Worked example (the `L_Level_Testing` instance): actor at X = 500, `SweepStart`
relative X = -1818, `SweepEnd` relative X = +819 -> rail 2637 uu, blade 1818 uu
from the start, so `A0 = 0.69`. With `TransitionDuration = 2` the first leg is
`0.62 s` toward `SweepEnd` or `1.38 s` toward `SweepStart`.

**Why `Select Vector` and not a Branch:** both outcomes continue to the same
`Set TargetScale3D`, so a branch would need a merge node. Select is pure and
keeps one execution chain.

**Why the projection and not `SweepProgress = 0`:** with `0` the first tick
would jump the blade to `SweepStart`; the old code did that explicitly with a
`TrapRoot -> Set Relative Location (StartLocation)` call, which is exactly the
"teleports when I walk near it" bug. Do not put that call back. If a blade is
placed off the rail, the projection clamps it to the nearest end and the first
tick pulls it onto the line - a perpendicular hop, by design.

**Do not** re-add `Set TransitionDuration`/`MorphElapsed`/`bTransitioning =
true` here. The old morph tail (branch on `TransitionDuration > 0`, then
`FinishSawMorph`, then a per-frame swap of the endpoints) is what caused the
original per-frame flip.

### 5.2 `FinishSawMorph` function (legacy)

The function body can stay - it is harmless while `bTransitioning` is never
set - or be deleted. It is kept in the current asset only to avoid a risky
graph edit late in the feature.

It used to own the `Sprite -> Play` call. That call now lives in `ActivateSaw`
(right after the visibility and collision setup), so the blade starts spinning
as soon as the trap fires, not when a morph completes. Do not add a second
`Play` elsewhere.

### 5.3 `Event BeginPlay`

Use a **Sequence** with three `then` pins. The Sequence is what runs the three
independent setup lanes without needing to manually merge Branch outputs.

```
Event BeginPlay
  -> Sequence
       Then 0:
         SET bActive = false
         SET bTransitioning = false
         SET StartScale3D = Make Vector(StartScale, StartScale, StartScale)
         TrapRoot -> Set Relative Scale 3D (New Scale 3D = StartScale3D)
         SET StartLocation = TrapRoot -> Get Relative Location
         Sprite -> Set Collision Enabled (New Type = NoCollision)
         Sprite -> Set Looping (bNewLooping = true)
         Sprite -> Play

       Then 1:
         Branch (Condition = GET bStartHidden)
           True  -> Sprite -> Set Visibility (false, propagate = true)
                    Trigger -> Set Collision Enabled (NoCollision)
           False -> Sprite -> Set Visibility (true, propagate = true)
                    Trigger -> Set Collision Enabled (QueryOnly)

       Then 2:
         Branch (Condition = GET bActivateOnPlayerNear)
           True  -> RevealBox -> Set Collision Enabled (QueryOnly)
           False -> RevealBox -> Set Collision Enabled (NoCollision)
                    ActivateSaw (call)
```

**Read the combinations:**

- `bStartHidden=false`, `bActivateOnPlayerNear=false`: visible, spinning,
  lethal at BeginPlay. This is the normal obstacle.
- `bStartHidden=false`, `bActivateOnPlayerNear=true`: visible **still** blade,
  lethal trigger already on, `RevealBox` armed. This is the visible saw-off
  surprise.
- `bStartHidden=true`, `bActivateOnPlayerNear=true`: invisible, trigger off,
  `RevealBox` armed. This is the hidden trap.
- `bStartHidden=true`, `bActivateOnPlayerNear=false`: hidden for the first
  evaluation, then `ActivateSaw` shows it immediately.

**The inherited `Trigger` is deliberately still enabled for the visible
saw-off case.** A visible blade is a normal obstacle; touching it kills even
before it turns on. Only hidden saws disable the trigger, because the player
must not die to something they cannot see.

### 5.4 `RevealBox` overlap

Select **`RevealBox`** in the Components panel -> Details -> **Events** -> click
**+** next to **On Component Begin Overlap**. Do not use the actor-level
`Event Receive Actor Begin Overlap`; the inherited disabled event at the top of
the graph is not the saw trigger.

```
On Component Begin Overlap (RevealBox)
  -> Equal (Object)
       A = Other Actor
       B = Get Player Character (Player Index = 0)
  -> Branch (Condition = Equal.Return Value)
       True  -> ActivateSaw
       False -> (nothing)
```

This is the **second** and **only** player gate in the saw. `BP_TrapBase`
already owns the lethal gate on `Trigger`; this one makes sure a bullet or an
enemy walking through `RevealBox` cannot start the trap.

### 5.5 `Event Tick` - the triangle sweep

This is the whole movement system. It replaces the old
`Branch (bTransitioning)` / `SawTick_Morph` lane.

```
Event Tick
  -> Branch (Condition = AND)
       A = GET bActive
       B = GET bMovable
       True:
         Max     (A = GET TransitionDuration, B = 0.01)      <- guards /0
         Divide  (A = Event Tick.Delta Seconds, B = Max.Return Value)
         Add     (A = GET SweepProgress, B = Divide.Return Value)
         Fmod    (A = Add.Return Value, B = 2.0)
         SET SweepProgress = Fmod.Return Value               <- stays in 0..2

         Greater  (A = GET SweepProgress, B = 1.0)           <- on the way back?
         Subtract (A = 2.0, B = GET SweepProgress)
         Select (Float)                                       -> PingAlpha
             Index    = Greater.Return Value
             Option 0 = GET SweepProgress
             Option 1 = Subtract.Return Value

         Fmod (A = GET SweepProgress, B = 1.0)               -> LoopAlpha

         Select (Float)                                       -> Alpha
             Index    = GET bPingPong
             Option 0 = LoopAlpha
             Option 1 = PingAlpha

         VLerp (A = StartLocation, B = TargetLocation, Alpha = Alpha)
           -> TrapRoot -> Set Relative Location

         VLerp (A = StartScale3D, B = TargetScale3D, Alpha = Alpha)
           -> TrapRoot -> Set Relative Scale 3D

       False:
         (existing chase gate; unreachable, see 5.6)
```

`DeltaSeconds` comes from the `Event Tick` node's own pin. Both `VLerp` nodes
are **Lerp (Vector)**; the alpha pin is the float `Alpha`.

The **scale** lerp lives here too, which is why a `bMovable = false` saw never
resizes - the whole True side is skipped. If you ever want a static saw that
grows, that needs its own lane; do not move the sweep maths out of this gate.

**Why this cannot teleport:** `SweepProgress` is a monotonic accumulator. The
tick only reads it through `Fmod`, so it wraps every 2 units; `PingAlpha` is a
triangle (0 -> 1 -> 0) and every value in between is produced on the way. There
is no "finished" event, no endpoint swap, and no state that can flip every
frame. The one intentional discontinuity is `bPingPong = false`, where the
loop alpha wraps `1 -> 0` once per cycle.

### 5.6 Legacy chase gate (do not enable)

The False side of the tick branch still contains the old
`AND(bActive, AND(bMovable, bChasePlayer)) -> ChaseStep` gate. It cannot run:
`bMovable` is `false` on that path, and the chase gate requires it to be
`true`. `bChasePlayer` is therefore inert.

`ChaseStep` itself is unchanged and still homes on the player's 3D position
with no pathfinding, no range check and no plane lock. It is not part of the
saw design; the rail concept replaced it. If chase is ever wanted, treat it as
a new feature with a Y-zeroing step and a max range, and give it its own mode
switch instead of overloading `bMovable`.

---

## 6. Per-instance recipes

Set these on the **placed actor** (Details -> Default), not on the class
defaults, unless every saw in the level should share the value.

| Scenario | `bStartHidden` | `bActivateOnPlayerNear` | `bMovable` | `bPingPong` | `StartScale` | `TargetScale` | `TransitionDuration` |
|---|---|---|---|---|---|---|---|
| Normal visible obstacle | false | false | false | - | 1.0 | 1.0 | - |
| Visible saw-off (spin on reveal) | false | true | false | - | 1.0 | 1.0 | - |
| Grow-on-reveal | false | true | true | - | 0.5 | 1.5 | 0.35 |
| Hidden stationary pop-up | true | true | false | - | 0.05 | 1.0 | - |
| **Rail saw (default)** | false | true | true | true | 1.0 | 1.0 | 2.0 |
| Hidden rail saw | true | true | true | true | 0.5 | 1.0 | 2.0 |
| One-way pass | false | true | true | false | 1.0 | 1.0 | 1.5 |

`TransitionDuration` is now **seconds per leg** (one crossing), so a full
back-and-forth cycle of a ping-pong saw takes `2 * TransitionDuration`.

The scale lerp lives in the same `Event Tick` lane as the sweep, so it needs
`bMovable = true`. A `bMovable = false` saw keeps whatever `StartScale` it was
given at BeginPlay: "grow-on-reveal" is therefore a **movable** recipe with the
two sweep gizmos sitting on the actor (`SweepStart == SweepEnd`), and a static
pop-up appears at `StartScale` rather than growing into it.

### 6.1 Normal visible obstacle

1. `bStartHidden = false`.
2. `bActivateOnPlayerNear = false`.
3. `bMovable = false`.
4. `StartScale = TargetScale = 1.0`.
5. Place the actor centre where the blade centre should be.

The saw spins from BeginPlay and the inherited `Trigger` kills the player on
contact. `RevealBox` is disabled at BeginPlay; it has no role in this recipe.
`SweepStart`/`SweepEnd` may be left wherever they are - they are not read.

### 6.2 Visible saw-off (spin on reveal)

1. `bStartHidden = false` - the player sees the still `SPR_SawOff` frame.
2. `bActivateOnPlayerNear = true` - it waits for `RevealBox`.
3. `bMovable = false` - no translation, no resizing.
4. `StartScale = TargetScale = 1.0`.
5. `RevealBox` extent: `(250, 100, 350)` so it also catches a player who jumps
   over the blade.

The blade is lethal before the reveal (inherited `Trigger` is on) and starts
spinning when the player enters the box.

**To make it grow instead**, set `bMovable = true`, put `SweepStart` and
`SweepEnd` both on the actor (coincident), and use `StartScale = 0.5`,
`TargetScale = 1.5`, `TransitionDuration = 0.35`. The location lerp then has
zero length and only the scale changes - the tick owns both.

### 6.3 Hidden stationary pop-up

1. `bStartHidden = true` - invisible and harmless before reveal.
2. `bActivateOnPlayerNear = true`.
3. `bMovable = false` (adds no motion; see below for the grow variant).
4. `StartScale = TargetScale = 1.0`.
5. `RevealBox` extent: `(250, 100, 250)`

`BeginPlay` hides the sprite and sets `Trigger` to `NoCollision`.
`RevealBox` is armed. When the player enters it, `ActivateSaw` shows the blade,
enables the lethal trigger, and starts the spin - at the size it already has.
For a blade that grows *out of the floor*, use `bMovable = true` with both
sweep gizmos on the actor, `StartScale = 0.05`, `TargetScale = 1.0` (6.2).

### 6.4 Rail saw (the shipped case)

1. `bStartHidden = false` (or `true` for a hidden rail saw).
2. `bActivateOnPlayerNear = true` (or `false` for always-on).
3. `bMovable = true`.
4. `bPingPong = true`.
5. `bSweepTowardEnd = true` (right first) or `false` (left first).
6. `StartScale = TargetScale = 1.0` for a pure translation.
7. `TransitionDuration = 2.0` (seconds per leg).
8. Drag `SweepStart` and `SweepEnd` to the ends of the run:
   - same Z, `Y = 0` -> horizontal sweep;
   - same X, different Z -> vertical sweep;
   - any diagonal is legal, but a pixel-platformer corridor usually wants one
     axis exactly equal.

The actor is **where the blade rests**. On activation the blade does not move -
it starts sliding from that spot toward the end picked by `bSweepTowardEnd`,
then ping-pongs over the whole rail.

Keep the blade on the line (same Y and Z as the gizmos). A blade placed off the
rail is clamped to the nearest end and pulled onto the line on the first tick.

### 6.5 One-way pass

1. `bMovable = true`, `bPingPong = false`.
2. `TransitionDuration` = seconds per crossing.
3. `SweepStart`/`SweepEnd` as above.

The blade crosses, then wraps back to the start in one frame. Use it when the
saw should "cut in from off-screen" repeatedly; use ping-pong when the player
must be able to read the timing.

---

## 7. PIE checklist

Run in `L_Level_Testing` with one instance of each recipe. **Never** save
`L_Level_01` while testing.

1. **Static saw:** `bMovable = false` -> the saw stays exactly where placed and
   still kills on contact.
2. **Rail saw, placement:** before activation it sits at its placed spot; on
   activation it **stays there** and starts sliding - no jump to either gizmo.
3. **Rail saw, direction:** flip `bSweepTowardEnd` -> the first slide starts
   toward the other end (nothing else changes).
4. **Rail saw, timing:** one leg takes `TransitionDuration` (stopwatch or log);
   `2.0` should read as a slow, readable sweep. The **first** leg is shorter if
   the blade was parked away from the end it heads to (it covers the remaining
   fraction only).
5. **Rail saw, reversal:** at both ends it changes direction smoothly; no
   flicker, no per-frame ping-pong between the ends.
6. **Rail saw, full cycle:** a ping-pong saw returns to `SweepStart` after
   `2 * TransitionDuration`.
7. **One-way:** `bPingPong = false` -> crosses once per `TransitionDuration`
   and wraps.
8. **Damage along the line:** stand at the far end (`SweepEnd`), let the blade
   arrive -> the player dies there. The hitbox must not stay at the placement
   point.
9. **Bullets / enemies:** fire through the blade and through `RevealBox` ->
   nothing activates, nothing is damaged.
10. **Hidden saw:** invisible and harmless before reveal; visible, lethal and
    sweeping after.
11. **Visible saw-off:** is lethal even before activation (inherited `Trigger`
    stays on).
12. **Respawn:** die and reload -> every saw returns to its placed origin form
    and hidden state.
13. **Two saws, different durations:** change `TransitionDuration` on one
    instance only -> the other keeps its own speed (proves the value is read
    per instance, not from the class default).

---

## 8. Verify

There is no automated verifier for this Blueprint in the current tree
(`Scripts/_verify_saw.py` and `Scripts/_verify_traps.py` are referenced by older
revisions of this guide but are not present). Verification is done by exporting
the asset and reading the graph, plus the PIE probes:

```bat
:: graph export (read-only, needs the editor open, PIE stopped)
set EXPORT_BASE=BP_Trap_Saw_New
set EXPORT_PATH=/Game/DontTrustTheLevels/Traps/Blueprints/BP_Trap_Saw_New
set EXPORT_OUT=%TEMP%\sawfinal
py -3 Scripts\_export_base_t3d.py

:: placed-instance switches + gizmo offsets
py -3 Scripts\_probe_saw_instance2.py

:: per-tick TrapRoot.x sampler (the probe that proved the sweep)
py -3 Scripts\_probe_saw_speed.py

:: activation state after a reveal (MorphElapsed/MorphAlpha are legacy now)
py -3 Scripts\_probe_saw_reveal.py
py -3 Scripts\_probe_saw_all.py
```

What to look for in the export:

- `ActivateSaw` `Select` (Vector): `Option 1` linked to `SweepStart`'s
  `RelativeLocation`, `Option 0` to `TrapRoot`'s, `Index` to `bMovable`.
- `Set TargetLocation` linked to `SweepEnd`'s `RelativeLocation`.
- `Set SweepProgress` linked to the `SelectFloat` result - not to a `0.0`
  literal.
- `ActivateSaw` contains **no** `Set Relative Location` call. If it does, the
  blade will jump to `SweepStart` on activation - that was the open bug.
- The phase chain: `Subtract(SweepEnd, SweepStart)`, `Subtract(TrapRoot,
  SweepStart)`, two `DotProduct`s, `Max(x, 0.01)`, `Divide`, `FClamp(0,1)`,
  `2 - A0`, `SelectFloat`.
- `SelectFloat.bPickA` = `bSweepTowardEnd`, with `A = A0` and `B = 2 - A0`
  (true returns `A`; the two are easy to swap).
- The tick gate is `AND(bActive, bMovable)`, and the two `VLerp` nodes take
  `StartLocation`/`TargetLocation` and `StartScale3D`/`TargetScale3D`.
- No exec path from `ActivateSaw` reaches `FinishSawMorph`.

`_probe_saw_speed.py` is the functional test: a correct sweep prints samples
that move monotonically for one leg, then reverse once; the old broken build
printed a reversal every ~10 ms.

---

## 9. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Does not move | `bMovable = false`, `bActive = false` (never activated), or `TransitionDuration` clamped to `0.01` (looks instant). |
| Moves once and stops | `bPingPong = false` and you are seeing the wrap as a stop; set it true for a rail saw. |
| Jumps between the endpoints every frame | the old morph path is running again: `bTransitioning` must stay `false`, and the tick gate must be `bActive AND bMovable`, not `bTransitioning`. |
| Teleports to `SweepStart` when the player walks near | a `TrapRoot -> Set Relative Location` node is still in `ActivateSaw` (this is the bug fixed in 5.1). Delete it; nothing in `ActivateSaw` should write `TrapRoot`'s transform. |
| First slide goes the wrong way | `SelectFloat`'s `A`/`B` are swapped. That function returns `bPickA ? A : B`, so `A` must be `A0` (toward `SweepEnd`) and `B` must be `2 - A0`. |
| Small sideways hop on the first frame | the blade is parked off the rail (Y or Z differs from the gizmos); the phase clamps to the nearest end and the tick pulls it onto the line. |
| Only half the rail is ever used | `StartLocation` is reading `TrapRoot` instead of `SweepStart`, or `TargetLocation` is not `SweepEnd`; check the `Select` (Vector) polarity and the target getter. |
| Sweeps on the wrong axis | `SweepStart`/`SweepEnd` differ in the wrong component; drag the gizmos with the level viewport in the XZ plane. |
| Blade leaves the line | `SweepStart`/`SweepEnd` are parented under `TrapRoot` instead of `DefaultSceneRoot`. |
| Blade is off-centre on the line | `Sprite` relative location is not `(-50,0,50)` or its scale is not `0.4211`. |
| Size pulses during the sweep | `StartScale != TargetScale`; the lerp is applied to scale too. Set them equal for a pure move. |
| It never changes size | resizing needs `bMovable = true` (the scale lerp is inside the sweep lane); a `bMovable = false` saw keeps its `StartScale`. |
| Hitbox stays behind | `Trigger` was not attached to `TrapRoot`; reattach it. |
| Hidden saw kills before it is revealed | `BeginPlay`'s `bStartHidden` True branch did not set `Trigger` to `NoCollision`. |
| Hidden saw never appears | `RevealBox` collision is `NoCollision`, the overlap event is missing, or `bActivateOnPlayerNear` is false. |
| Bullets or enemies reveal the saw | the `Equal` node is missing or wired to the wrong actor; use `OtherActor` and `Get Player Character(0)`. |
| Visible saw-off never turns on | `RevealBox` is disabled, the overlap event is missing, or `ActivateSaw` sits on the False pin. |
| Player dies twice / reloads twice | a `Kill` or `Apply Damage` node was added to the child. Delete it; `BP_TrapBase` owns player death. |
| The saw blocks the player | `Sprite` collision is not `NoCollision`; the lethal volume is `Trigger`. |
| Blade sits on the off frame | the flipbook is stopped and nothing calls `Play`; `ActivateSaw` must call `Sprite -> Play` after `Stop` + `Set Playback Position(0)`. |
| `Lerp` has the wrong type | use **Lerp (Vector)** for both vector pairs; the alpha stays a float. |
| `Fmod` / `Select` not in the node search | right-click with **Context Sensitive** off; `Fmod` is `Float % Float`, `Select` is under *Utilities -> Select*, `Select Float` is the math-function twin. |
| Scene Components `SweepStart`/`SweepEnd` missing from the instance | they are local to `BP_Trap_Saw_New`; re-add them under `DefaultSceneRoot` and compile. |

---

## 10. Design notes

- **One class, per-instance data.** No per-level saw Blueprint copies. The
  placed actor owns `bStartHidden`, `bActivateOnPlayerNear`, `bMovable`,
  `bPingPong`, `bSweepTowardEnd`, `StartScale`, `TargetScale`,
  `TransitionDuration` and the two sweep gizmos.
- **The lethal gate stays in `BP_TrapBase`.** The child never calls `Kill` or
  `Apply Damage`; this is what keeps the enemy/bullet trap contract intact.
- **Reveal and damage are different volumes.** `RevealBox` is a proximity
  sensor; `Trigger` is the lethal hitbox. Do not make one volume do both, or a
  hidden saw becomes lethal before it is shown.
- **`TrapRoot` is the animation pivot.** `Sprite` and `Trigger` are its
  children. Scaling it grows the visual and the hitbox together; moving it
  moves both - which is exactly what makes a sweeping saw lethal along its
  whole line.
- **Two gizmos beat an offset number.** `SweepStart`/`SweepEnd` are draggable
  per instance, so a designer can place a rail without editing defaults, and a
  zero-length sweep (`Start == End`) is a valid static pose.
- **The blade starts where it was placed.** The projection turns "where is the
  actor?" into a phase on the rail, so activation never rewrites the transform.
  The one thing the designer must respect is that the blade sits **on** the
  line; off it, the clamp + first lerp produce a small perpendicular hop.
- **A triangle wave beats a state machine.** One accumulator, two `Fmod`s and
  two `Select`s replace `bTransitioning`, `MorphElapsed`, `MorphAlpha` and a
  finish callback. There is no edge case where the "end" fires every frame.
- **Tick cost is negligible.** The branch resolves on two bools before any
  float work, so a static saw costs one `AND` and one branch per frame. Twenty
  sweeping saws cost less than one particle system at this scale.
- **The off frame is real art, not a placeholder.** `FLB_Saw` frame 0 is
  pixel-identical to `SPR_SawOff`, so the same component can show the still
  blade and the spin.
- **Python cannot build the graphs.** `BlueprintFactory` can create the asset
  and set `BP_TrapBase` as parent, but this UE 4.27 build exposes no SCS
  component, variable, or K2-node creation API. The guide is the
  implementation; the export probes are the safety net.

---

## 11. Resolved: the history of this trap (15 Nov 2026)

Three separate faults were behind the reports in this document:

1. **The morph composite's tunnels were duplicated.** `SawTick_Morph` exposed
   two float inputs, `B` and `DeltaSeconds`; the inner `Add` read one of them.
   Whichever one was wired, the runtime showed `MorphElapsed = 0.000` next to
   `MorphAlpha = 0.167` and a blade that flipped between the two endpoints
   every ~10 ms. A hand-built composite has one input; this was a paste
   artifact.
2. **The `Select` in `ActivateSaw` was inverted.** `Option 1` is the true side,
   and it held `StartLocation`, so `bMovable = true` selected "stay where you
   are" as the target, while the instance's `TransitionDuration` was still
   `0.0` (a fresh instance default), which took the "finish immediately"
   branch anyway.
3. **`ActivateSaw` snapped the blade to `SweepStart`.** A plain
   `TrapRoot -> Set Relative Location (StartLocation)` call (not a branch) ran on
   every activation, so a saw placed anywhere except on the start gizmo
   teleported the moment `RevealBox` fired. It is deleted; `ActivateSaw` now
   seeds `SweepProgress` from the blade's own phase instead (5.1).

The fix for the first two was to stop repairing the composite and replace the
movement with the tick triangle wave in section 5.5. The morph nodes remain in
the asset as dead code; they are never executed because `bTransitioning` stays
`false`.

Final behaviour, confirmed in PIE. The second column is the phase the blade
starts at; in `L_Level_Testing` it is `0.69` (parked between the gizmos), so the
first leg is a partial one and every later leg is a full crossing:

| t (duration 2, starting at alpha 0.5) | `SweepProgress` | alpha | position |
|---|---|---|---|
| 0.0 s | 0.5 | 0.5 | where it was placed |
| 1.0 s | 1.0 | 1.0 | `SweepEnd` |
| 2.0 s | 1.5 | 0.5 | halfway back |
| 3.0 s | 2.0 -> 0.0 | 0.0 | `SweepStart` |
| 4.0 s | 0.5 | 0.5 | halfway |

The blade also spins from activation, because `Sprite -> Play` moved from
`FinishSawMorph` into `ActivateSaw` (after `Stop` + `Set Playback Position(0)`).

### Deferred ideas

- **Multiple legs:** replace `SweepStart`/`SweepEnd` with an array of scene
  components and an index, then walk the array with the same triangle alpha.
- **Per-instance easing:** feed `PingAlpha` through a curve before the `VLerp`
  for an ease-in/out rail.
- **External trigger:** keep `RevealBox` optional and let a corridor trigger
  actor call `ActivateSaw` on one or more saws. The function is already public
  and takes no arguments.
