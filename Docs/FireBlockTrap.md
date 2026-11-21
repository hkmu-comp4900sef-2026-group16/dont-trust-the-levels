# BP_Trap_Fire - fire block - build guide

**Status (20 Nov 2026)** — In the local Blueprint, PIE confirmed that player
overlap starts the fire cycle, bullets leave it idle, and the player can trigger
it again after it switches off. Recheck the 0.5-second timing and Y alignment
after applying the settings below. This trap inherits `BP_TrapBase` and uses
its player-only `Trigger` for damage.

---

## 1. Behaviour

The block is idle (off). When the player steps on it:

1. `FLB_Fire_Hit` plays immediately (the "ignition" telegraph).
2. After `Delay` seconds (default **0.5**), `FLB_Fire_On` starts and loops.
3. Fire stays on for `FireDuration` seconds (default **2.0**), then the block
   returns to the off state.
4. If the player steps on the block while the fire is on, the inherited
   `Trigger` kills them.
5. If the player is already standing on the block when the fire turns on, they
   must also die (see 5.3 - verify this case).

`Delay` and `FireDuration` are **instance-editable** floats.

---

## 2. Art facts (verified)

| Fact | Value |
|---|---|
| Texture | `T_Fire_Hit_D`, `T_Fire_On_D`, `T_Fire_Off_D` |
| Frame size | 16 x 32 px |
| Pixels per unreal unit | `0.16` |
| Natural size | `100 x 200` uu |
| Hit | `FLB_Fire_Hit`, 4 frames, 12 fps |
| On | `FLB_Fire_On`, 3 frames, 12 fps |
| Off | `SPR_Fire_Off`, 1 sprite |
| Pivot | `TOP_LEFT` |

The off state is a **PaperSprite**, not a flipbook. The inherited `Sprite` is a
`PaperFlipbookComponent`, so create a 1-frame flipbook:

- Content Browser -> right-click `SPR_Fire_Off` -> **Create Flipbook** ->
  `FLB_Fire_Off` (1 frame, 12 fps). Use it as the idle/off animation.

If you do not want to create it, add a second `PaperSpriteComponent`
(`OffSprite`, `SPR_Fire_Off`) and toggle its visibility; the flipbook is cleaner.

---

## 3. Components

Create `Content/DontTrustTheLevels/Traps/Blueprints/BP_Trap_Fire`, parent
`BP_TrapBase`.

| Component | Parent | Relative location / scale | Key settings |
|---|---|---|---|
| `DefaultSceneRoot` | - | `(0,0,0)` / `1` | inherited root; do not rename |
| `Sprite` | inherited | `(-50, 0, 200)` / `1.0` | Flipbook = `FLB_Fire_Off`; Looping = off for Off/Hit, on for On; Collision = `NoCollision` |
| `Trigger` | inherited | `(0, 0, 50)` / `1` | `OverlapAllDynamic`, Generate Overlap Events on, Box Extent `(50,50,50)`, **disabled at BeginPlay** |
| `StepBox` | `DefaultSceneRoot` | `(0, 0, 50)` / `1` | `OverlapAllDynamic`, Query Only, Generate Overlap Events on, Box Extent `(50,50,50)`; this is the step sensor |

The actor origin is the **bottom centre** of the block. The 100x200 sprite is
placed with its top-left at `(-50, 0, 200)`, so it stands from the floor to two
tiles high and is centred on the actor's X.

`BP_TrapBase` now carries saw-oriented defaults, so `BP_Trap_Fire` must
**override** them (the verifier fails on the leftovers):

| Component | BP_TrapBase default | BP_Trap_Fire must be |
|---|---|---|
| `Trigger` | `(50, 0, -50)` | `(0, 0, 50)`, extent `(50,50,50)` |
| `Sprite` | `(0, 0, 0)`, `BlockAllDynamic`, no flipbook | `(-50, 0, 200)`, `NoCollision`, `FLB_Fire_Off` |

`Trigger` and `Sprite` are children of the inherited `TrapRoot` (at `(0,0,0)`),
so the numbers above are relative to the actor origin.

`Trigger` is the damage box; `StepBox` only starts the cycle. Do **not** add a
second `Kill` or `Apply Damage` in this Blueprint; `BP_TrapBase` owns the
player death.

---

## 4. Variables

| # | Name | Type | Default | Instance editable | Meaning |
|---|---|---|---|---|---|
| 1 | `Delay` | Float | `0.5` | yes | Seconds between the step and `Fire_On`. |
| 2 | `FireDuration` | Float | `2.0` | yes | Seconds the fire stays on. |
| 3 | `bCycleActive` | Boolean | `false` | no | Internal. True from step until the fire goes off. |
| 4 | `bBurning` | Boolean | `false` | no | Internal. True while `Fire_On` is active. |
| 5 | `GameplayPlaneY` | Float | `0.0` | yes | World Y of the player lane. Set a per-instance value for levels that use a different lane. |

Compile after adding them.

---

## 5. Graph

### 5.1 BeginPlay

```
Event BeginPlay
  -> Sequence
       Then 0:
         Sprite -> Set Flipbook (FLB_Fire_Off)
         Sprite -> Set Playback Position (0.0, false)
         Sprite -> Stop
         Sprite -> Set Collision Enabled (NoCollision)
         Trigger -> Set Collision Enabled (NoCollision)
         StepBox -> Set Collision Enabled (QueryOnly)
         SET bCycleActive = false
         SET bBurning = false
```

`Sprite` is visual only. The inherited `Trigger` is off until the fire is on.

### 5.2 `StepBox` On Component Begin Overlap

Select `StepBox` -> Details -> Events -> **+ On Component Begin Overlap**.

```
On Component Begin Overlap (StepBox)
  -> Equal (Object)
       A = Other Actor
       B = Get Player Character (0)
  -> Branch (Equal.Return Value)
       True -> Branch (GET bCycleActive)
            True  -> (nothing - cycle already running)
            False -> SET bCycleActive = true
                     Sprite -> Set Flipbook (FLB_Fire_Hit)
                     Sprite -> Set Looping (false)
                     Sprite -> Set Playback Position (0.0, false)
                     Sprite -> Play
                     Set Timer by Function Name
                       (Object = self, Function Name = FireOn, Time = GET Delay)
       False -> (nothing)
```

Only the player starts the trap. Bullets and enemies are ignored.

**Timer node:** use **Set Timer by Function Name** (the pattern already used in
the other enemy traps), with `Function Name` = `FireOn` / `FireOff`. The custom
event names must match the string exactly. The delegate version
(**Set Timer by Event**) also works; both pass the verifier.

### 5.3 `FireOn` (custom event, timer target)

```
FireOn
  -> Sprite -> Set Flipbook (FLB_Fire_On)
  -> Sprite -> Set Looping (true)
  -> Sprite -> Play
  -> Trigger -> Set Collision Enabled (QueryOnly)
  -> SET bBurning = true
  -> Set Timer by Function Name
       (Object = self, Function Name = FireOff, Time = GET FireDuration)
```

Enabling `Trigger` kills a player who steps in while the fire is on.

**Player already standing when it turns on:** test this. If the player survives,
`Trigger` did not fire a new overlap. Fix it in `BP_TrapBase` (not the child):

- Add a function `KillOverlappingPlayer` on `BP_TrapBase`:
  ```
  Trigger -> Get Overlapping Actors (Class Filter = Character)
    -> For Each Loop
       -> Equal (Other Actor == Get Player Character(0))
       -> True -> Kill (Message) Target = Other Actor
  ```
- Call `KillOverlappingPlayer` from `FireOn` after enabling `Trigger`.

This keeps the Kill in the base and still player-only. Do not put a `Kill` in
`BP_Trap_Fire`.

### 5.4 `FireOff` (custom event, timer target)

```
FireOff
  -> Sprite -> Set Flipbook (FLB_Fire_Off)
  -> Sprite -> Set Playback Position (0.0, false)
  -> Sprite -> Stop
  -> Trigger -> Set Collision Enabled (NoCollision)
  -> SET bBurning = false
  -> SET bCycleActive = false
```

The block can be triggered again after the fire ends.

**Optional retrigger while standing:** if the player never leaves the block,
`On Component Begin Overlap` will not fire again. If you want the block to
cycle while the player stands on it, at `FireOff` use
`StepBox -> Is Overlapping Actor(Get Player Character(0))` and, when true,
start the cycle again (same chain as 5.2's False pin). Otherwise it retriggers
only after the player steps off and back on.

### 5.5 Timer cleanup

If the trap is destroyed or the level restarts, clear pending timers. Use
`Set Timer by Function Name` with a `TimerHandle` variable only if you need to
cancel; for a short one-shot sequence the default behaviour is acceptable.

---

## 6. Per-instance setup

### 6.1 Align newly placed fire blocks to the player lane

In `BP_Trap_Fire`, open **Construction Script**. Connect its entry to
**Set Actor Location** with `Target = Self`. If the graph already calls its
parent, connect the new node after that call.

1. Add **Get Actor Location** with `Target = Self`. Right-click its
   `Return Value` and choose **Split Struct Pin**.
2. Split **Set Actor Location.New Location**. Connect the actor's current X
   to X and current Z to Z. Connect **Get GameplayPlaneY** to Y. Leave
   **Sweep** unchecked.
3. Compile and drag a new Fire Block into the level. In Details, confirm
   its Y matches `GameplayPlaneY`. X and Z follow the placement.
4. Set the placed actor's `GameplayPlaneY` in Details if the level's player
   lane uses a Y other than the class default of `0.0`.

### 6.2 Place and tune each fire block

1. Use `Delay = 0.5` and `FireDuration = 2.0` as the class defaults. For
   a previously placed actor with a timing override, reset its `Delay` in
   Details or enter `0.5` explicitly.
2. Place the actor's origin at the **bottom centre** of the block, on the
   surface of the level floor. The floor supports the player.
3. Size `StepBox` and `Trigger` to the block footprint. For one tile, use
   location `(0,0,50)` and extent `(50,50,50)`.
4. `Sprite` stays at `(-50,0,200)` and scale `1.0` for a 100x200 flame. For a
   larger block, scale the actor uniformly so `Trigger` grows with the art.

---

## 7. PIE checklist

1. Step on the block -> `Fire_Hit` plays, then after `Delay` the `Fire_On`
   loop starts, then returns to off after `FireDuration`.
2. With class defaults, verify ignition after 0.5 seconds and extinguishing after another 2.0 seconds. Then test an instance with `Delay = 0.25` and `FireDuration = 1.0`.
3. Step on while the fire is on -> player dies once.
4. Step on during Hit/Delay -> no death from the fire yet; the cycle continues.
5. Stand still on the block when `FireOn` happens -> player dies (see 5.3).
6. Fire a bullet through the block -> no trigger, no damage.
7. Walk an enemy through -> no trigger, no trap damage.
8. Wait for `FireOff`, step off and back on -> the cycle repeats.
9. Die/respawn -> the block returns to off and can trigger again.
10. Compile -> `Compile of BP_Trap_Fire successful`.
11. Drag a fresh actor into the level from the Content Browser. Confirm its
    Y matches `GameplayPlaneY` and the player can trigger it. Check that a
    placement on another lane follows its instance override.

---

## 8. Verifier

The shell, `FLB_Fire_Off` and the build guide are already created. Before PIE,
run the read-only structural verifier (editor open, PIE stopped):

```
py -3 Scripts/_verify_fire.py
```

It checks the inheritance, `StepBox`/`Trigger` placement and collision, the two
editable floats, `FLB_Fire_Off` (1 frame, 12 fps), the player gate, the
`bCycleActive` gate, both timers, the three flipbook states, and that
`BP_Trap_Fire` adds no second `Kill`.

`PENDING` = not built yet; `FAIL` = built but contradicts this guide. With the
fresh shell the three expected failures are the inherited saw defaults
(`Trigger` at `(50,0,-50)`, `Sprite` at `(0,0,0)` and `BlockAllDynamic`) that
the table in section 3 asks you to override.

UE Python cannot read the *Instance Editable* flag, so the verifier prints a
`WARN` for `Delay`/`FireDuration`; tick the eye icon on both yourself.
