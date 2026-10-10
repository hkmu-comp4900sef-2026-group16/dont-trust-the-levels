# DashAiming.md — Dash toward the cursor

**Owner:** Player pillar · **Branch:** `branch/Dennis` · **Status:** Part 1 done (ini), Parts 2–6 pending editor work

**Goal:** pressing **Spacebar** sends the player a fixed distance (`DashRange`) toward
wherever the crosshair is pointing — any direction in the screen plane, including
up/down diagonals, on the ground **or** mid-air. Walls/floors stop the dash early
(sweep collision), so travel is *up to* `DashRange`, never more.

Builds on `CrosshairAiming.md` (cursor, facing, and its Part 8 aim plan: *"deproject
the cursor and intersect the ray with the gameplay plane; keep aim data in the
PlayerController so weapons can call it"* — this doc builds that function).

## Design decisions

| Decision | Why |
|---|---|
| Sweep-based move (`AddActorWorldOffset` + `bSweep`), not `LaunchCharacter` | The request is a **certain range**. Launch gives a velocity whose distance depends on gravity; sweep gives exact distance and stops at geometry (can't tunnel into traps either). |
| `SetMovementMode(Flying)` during the dash | Freezes gravity so a straight-line dash stays straight; at end restore `Falling` (auto-lands into Walking). Jump input does nothing in Flying, so no extra gate is needed there. |
| Aim = deproject cursor → intersect plane Y = player's Y | Already specced in `CrosshairAiming.md`. The ortho camera looks straight down −Y, so the ray is never parallel to the plane — the division below is always safe. |
| One air-dash until landing (Celeste-style) | Without it, repeated straight-up dashes = infinite levitation. `bAirDashUsed` resets on `Event Landed`. Delete gate G2b if unlimited air-dashes are ever wanted. |
| Cooldown starts in `EndDash()` | Limits ground spam AND makes wall-blocked dashes pay too (a blocked dash moves ~0, so no wall-judder exploit). |
| Freeze the flipbook during dash (`NOT bIsDashing` added to the anim gate) | In Flying, `IsFalling` = false and velocity ≈ 0, so the composite would flip to Idle mid-dash. Freezing holds the last frame — mid-jump/mid-run frames read as a dash pose. Polish later: dedicated `FLB_Player_Dash` (unused `SPF_Player_WallJump_00–04` frames exist). |
| Key = data, not code | Graphs bind the **action name** `Dash`. Rebinding = edit one line in `Config/DefaultInput.ini` or Project Settings → Input — zero Blueprint changes. Tuning (`DashRange`/`DashDuration`/`DashCooldown`) = BP_Player Class Defaults, zero graph changes. |

## Architecture (who owns what)

| Piece | Asset | Why |
|---|---|---|
| `Dash` action mapping | `Config/DefaultInput.ini` | input is config, not logic |
| World aim point | `BP_PlayerController` → new function `GetAimWorldLocation` | PC owns aim data; Weapons pillar calls the same function later without casting to the pawn |
| Dash state machine | `BP_Player` event graph + variables | Player pillar owns movement feel |
| `EndDash()` | `BP_Player` function | one restore-state routine, called from 3 sites |

## Part 1 — Input mapping (done, text-only edit)

`Config/DefaultInput.ini` (edited while the editor was closed, so it loads cleanly next launch):

```diff
-+ActionMappings=(ActionName="Jump",Key=SpaceBar,bShift=False,bCtrl=False,bAlt=False,bCmd=False)
++ActionMappings=(ActionName="Dash",Key=SpaceBar,bShift=False,bCtrl=False,bAlt=False,bCmd=False)
```

**Spacebar was Jump; it is now Dash** (one key can't fire two actions). Jump remains
on **W**, **Up** and **Gamepad_FaceButton_Bottom**.

## Part 2 — BP_PlayerController: function `GetAimWorldLocation`

New function on `BP_PlayerController`, **return type Vector, no inputs**. Math:

```
PlaneY   = pawn actor location . Y          (the 2D gameplay plane)
t        = (PlaneY − RayOrigin.Y) / RayDir.Y
AimPoint = RayOrigin + RayDir × t           (cursor's world point on the plane)
```

| # | Node | Wiring |
|---|---|---|
| 1 | **DeprojectMousePositionToWorld** (Target = self) | **no data inputs** — reads the cursor itself → `WorldLocation` (ray origin), `WorldDirection` |
| 2 | **GetPawn** (Target = self) | → `Pawn` |
| 3 | **GetActorLocation** (Target = Pawn from #2) | → `Location` |
| 4 | **BreakVector** ×3 | break #1 `WorldLocation` → `Y`; break #1 `WorldDirection` → `Y`; break #3 `Location` → `Y` (= PlaneY) |
| 5 | **Subtract (float − float)** | `PlaneY − RayOriginY` |
| 6 | **Divide (float ÷ float)** | (#5) ÷ `RayDirY` → `t` |
| 7 | **Multiply (Vector × Float)** | `WorldDirection` × `t` |
| 8 | **Add (Vector + Vector)** | `WorldLocation` + (#7) → `AimPoint` |
| 9 | **Return node** | `ReturnValue ← AimPoint` |

Exec chain: **`Entry → Return` (one direct white wire)** — in 4.27 the whole cursor family is
**pure**: `GetMousePosition` (proven — the BP_Player facing chain uses it floating, no exec,
and works in PIE) and `DeprojectMousePositionToWorld` (data pins only in the palette).
Pure nodes take no exec wire; they evaluate whenever their outputs are read, so the
deproject just floats as a data node feeding the math chain. If your palette version
*does* show exec pins on it, wire `Entry → DeprojectMousePositionToWorld → Return`
instead — identical result.

## Part 3 — BP_Player: new variables (Category `Dash`, instance, ReadWrite)

| Variable | Type | Default | Meaning |
|---|---|---|---|
| `DashRange` | Float | 512.0 | travel distance in uu (100 uu = 1 tile → ~5 tiles) |
| `DashDuration` | Float | 0.15 | seconds the dash takes |
| `DashCooldown` | Float | 0.75 | seconds until the next dash is offered |
| `bIsDashing` | Bool | false | active-dash flag (gates movement input, anim, re-dash) |
| `DashDir` | Vector | (0,0,0) | unit direction of the current dash |
| `DashDistanceRemaining` | Float | 0.0 | how much of `DashRange` is left |
| `DashCooldownRemaining` | Float | 0.0 | cooldown countdown |
| `bAirDashUsed` | Bool | false | one air-dash until landing; reset by `Event Landed` |

Tuning later = open BP_Player **Class Defaults**, change `DashRange`/`DashDuration`/
`DashCooldown`, Compile — no graph edits, no re-verification.

## Part 4 — BP_Player: Dash input chain

Right-click the event graph → type `Dash` → **Action Events → Dash** (use only the
**Pressed** exec pin). Chain — all gates *before* any state change:

| Step | Node | Detail |
|---|---|---|
| G1 | Branch | `bIsDead`? → true: stop |
| G2 | Branch | `bIsDashing`? → true: stop (no dash-in-dash) |
| G3 | Branch | `DashCooldownRemaining > 0`? → true: stop |
| G2b | Branch ×2 | 1st Branch: `IsFalling` (CharacterMovement)? → **false: continue** (grounded dash — do NOT consume the air-dash). true → 2nd Branch: `bAirDashUsed`? → true: stop. false → `SET bAirDashUsed = true`, continue |
| A | **GetPlayerController(0)** → **Cast to BP_PlayerController** → **GetAimWorldLocation** | → `AimPoint` |
| B | **GetActorLocation** | → `PlayerLoc` |
| C | **Subtract (Vector − Vector)** | `AimPoint − PlayerLoc` |
| G4 | Branch | `VSize(C) > 32`? → false: stop (cursor basically on the player) |
| S1 | **GetUnitDirection** (`From = PlayerLoc`, `To = AimPoint`) → `SET DashDir` | unit vector |
| S2 | `SET DashDistanceRemaining = DashRange` | |
| S3 | `SET bIsDashing = true` | |
| S4 | **LaunchCharacter** `(0,0,0)`, `bXYOverride ✓`, `bZOverride ✓` | kills run-velocity carryover |
| S5 | **CharacterMovement → SetMovementMode** = `Flying` | no gravity / no walk input during dash |

## Part 5 — BP_Player: Tick dash processing + gates

Tick ends in a Sequence (`K2Node_ExecutionSequence_0`): pin 1 → animation composite.
Right-click the Sequence → **Add Pin**; pin 2 → dash processing:

**Branch: `bIsDashing`?**
- **False → cooldown countdown** — Branch (`DashCooldownRemaining > 0`?) → true:
  `SET DashCooldownRemaining = DashCooldownRemaining − DeltaSeconds`.
- **True → dash step:**
  1. Branch: `bIsDead`? → true: **`EndDash()`** (corpse doesn't keep flying)
  2. `StepLen` (pure float): `DeltaSeconds / DashDuration` → **Multiply** × `DashRange`
  3. `Step` (pure vector): **Multiply Vector × Float** — `DashDir × StepLen`
  4. **AddActorWorldOffset** (self, `Delta = Step`, `bSweep ✓`) → **BreakHitResult** → `bBlockingHit`
  5. Branch: `bBlockingHit`? → true: **`EndDash()`** (dash stopped by wall/floor — range was shorter)
  6. `SET DashDistanceRemaining = DashDistanceRemaining − StepLen`
  7. Branch: `DashDistanceRemaining <= 0`? → true: **`EndDash()`**

### `EndDash()` — new function on BP_Player (no inputs, no returns)

| # | Node |
|---|---|
| 1 | `SET bIsDashing = false` |
| 2 | **CharacterMovement → SetMovementMode** = `Falling` (engine auto-transitions to Walking on landing) |
| 3 | `SET DashCooldownRemaining = DashCooldown` |

### AddMovementInput gate (drift guard)

`InpAxisEvt_MoveRight` currently ends in AddMovementInput. Insert a Branch before it:
Condition = `NOT bIsDashing` → true → AddMovementInput. (During dash the axis event
must not add sideways drift — the sweep is the only mover.)

### `Event Landed` (new event on BP_Player)

Character event **Landed** → `SET bAirDashUsed = false`. (Respawn needs nothing —
the level reloads, which resets instance defaults.)

## Part 6 — Animation during dash (freeze, one node edit)

The anim composite's first gate (`IfThenElse_5`) tests `NOT bIsDead`. Change its
Condition to:

```
(NOT bIsDead) AND (NOT bIsDashing)
```

Add an **AND** node: `A` = the existing `NOT bIsDead` output, `B` = `NOT bIsDashing`.
Nothing else in the composite changes — the Part 10 fix and the grounded
`VSize > 10` chain stay exactly as verified in `02a1022`. While dashing no
`SetFlipbook` runs, so the sprite holds its last frame; the tick after `EndDash()`
the composite resumes normally.

## Part 7 — Verify (PIE on `L_Level_00`)

| Check | Expected |
|---|---|
| Spacebar with cursor right | dash ~5 tiles right, then resumes Running/Falling |
| Cursor up-right | diagonal up-right dash (straight line, no gravity arc) |
| Dash at a wall | stops **at** the wall, falls straight down; cooldown still applies |
| Dash at the floor while standing | stops immediately (blocked) — aim before dashing |
| Jump (W), dash mid-air | dash works once; air-dash **not** offered again until landing |
| Air-dash then double-jump | double jump still available (dash never touches `JumpCurrentCount`) |
| Hold A/D during dash | no sideways drift |
| Double-tap Spacebar fast | second dash blocked by `bIsDashing` + cooldown |
| Cursor resting on the player | nothing happens (`VSize ≤ 32` gate) |
| Die mid-dash (spikes) | corpse stops, Hit plays, level reloads as before |
| Sprite during dash | frozen pose (no Idle flip); resumes right after |
| Crosshair + facing during dash | still tracks/faces the cursor |
| Regressions | Jump/Fall/DoubleJump anims (02a1022 fix), grounded Run/Idle, death chain |

After PIE passes, verify on disk the same way as Phase 2 (headless re-export +
`_bp_graph_map.ps1`): expect `GetAimWorldLocation` on the PC, the input chain ending
in `SetMovementMode(Flying)`, `AddActorWorldOffset` with sweep in Tick, three
`EndDash` callers, the axis-event gate, and the composite's AND gate.

## Troubleshooting

| Symptom | Cause → fix |
|---|---|
| Spacebar jumps (or does nothing) | Stale/duplicate mapping: `DefaultInput.ini` is only read at editor start — close and reopen the editor after editing it; confirm exactly **one** SpaceBar line, under action `Dash` |
| Player both jumps and dashes | SpaceBar mapped to both actions — remove one mapping |
| Dash is instant / one frame | `bBlockingHit` true every frame: check `bSweep ✓` and that you aren't starting inside geometry |
| Dash always goes one fixed way | `GetUnitDirection` From/To swapped (From = **player**, To = **aim**) |
| Character floats after dash | `EndDash` left `Flying` — its SetMovementMode must be `Falling` |
| Dash drifts sideways | AddMovementInput gate (Part 5) missing |
| Sprite flips to Idle mid-dash | Part 6 AND gate missing or miswired |
| Infinite climbing by spamming up-dashes | expected without G2b — keep the air-dash gate |
| Aim point looks 3D / behind the player | plane Y must come from the **pawn's** location (nodes #2 → #3), not the camera |
| Node has no exec pins | It's a **pure** function (`GetMousePosition`, `DeprojectMousePositionToWorld` in 4.27) — don't wire exec into it; wire exec *around* it (`Entry → Return`) and connect only its data pins |
| No dash at all | Action name must be exactly `Dash` in both the ini and the BP event node |

## Commit

Editor closed for git ops; `git pull` first; one feature per commit (CLAUDE.md §3, §6).

- Message: `feat: dash toward cursor aim with air-dash limit (player)`
- Files: `Config/DefaultInput.ini` · `Content/DontTrustTheLevels/Core/Blueprints/BP_PlayerController.uasset` · `Content/DontTrustTheLevels/Player/Blueprints/BP_Player.uasset` · `Docs/DashAiming.md`
- Binaries via Git LFS (`*.uasset`; see `LfsLocking.md` if lock contention appears)