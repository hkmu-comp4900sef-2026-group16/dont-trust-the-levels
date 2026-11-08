# Enemy Work Plan — three-slot parallel execution

**Status (4 Nov 2026):** execution plan for the remaining enemy work. Owner **B
has been retired**; their four assets and their milestone (`M2`) now belong to
**A2**. The live slots are **A1, A2, C**. This file assigns the work, defines
the dependency gates and lists the acceptance tests. It does **not** replace the
technical design:

| Authority | File | What it decides |
|---|---|---|
| 1 | **`Docs/EnemyAI.md`** | movement, patrol, aggro, knockback, rescue; wins on conflict |
| 2 | **`Docs/Enemies.md`** | variables, graph recipes, per-enemy mechanics, test matrix |
| 3 | **`Docs/EnemyPlacement.md`** | level placement rules and per-enemy layouts |

**Audience:** Owner A1, Owner A2, Owner C and their AI assistants. Read this file
first, then the exact sections named in your work card. Do not infer rules from
old summaries. **Owner B no longer exists:** anything in this file that used to
say `B` now says `A2`, including the four stationary/flyer assets and
`L_Level_Testing`.

**Scope:** the nine active enemy mechanics plus the projectile/puddle/shooter
support assets. `BP_PeaPlant` and `BP_EnemyProjectile_Pea` are **out of scope**
unless the design changes.

---

## 0. Owner slots

Fill in the real names before work starts. Do not change asset ownership without
updating this table and taking the Git LFS lock.

| Slot | Name / GitHub | Workstream | Assets | Can start |
|---|---|---|---|---|
| **A1** | base owner | shared base AI + first walker | `BP_EnemyBase`, `BP_EnemyPlatform`, `BP_Snail`, contract docs | now |
| **A2** | rocks + stationary/flyers + level | rock split, the four no-walker assets, level integration | `BP_RockBase`, `BP_Rock1/2/3`, `BP_SpikeTurtle`, `BP_Ghost`, `BP_Bat`, `BP_FloatingSkull`, `L_Level_01`, `L_Level_Testing` | now |
| **C** | groupmate 2 | support + ranged/walkers | `BP_EnemyProjectile`, `BP_EnemyProjectile_Wood`, `BP_ToxicPuddle`, `BP_ShooterEnemyBase`, `BP_WoodLog`, `BP_ToxicSlime`, `BP_Rhino` | now |

**Owner B is retired (4 Nov 2026).** Everything B owned moved to A2:
`BP_SpikeTurtle`, `BP_Ghost` and `BP_Bat` are **DONE** and become A2 regression
assets (do not rebuild them); `BP_FloatingSkull` is the one remaining build;
`L_Level_Testing` is now A2's scratch PIE map. A2 therefore carries the largest
load, and §4.2 / §6 fix a hard order for A2: Skull first, then Rocks, then the
maps.

A1 is the only person allowed to edit `BP_EnemyBase`, `BP_EnemyPlatform` and
`BP_Snail`. A2 is the only person allowed to edit the Rock assets, the four
stationary/flyer assets and both level maps. A1 may prepare Snail
variables/defaults/art; A2 may prepare Rock and Skull variables/defaults/art and
stage static map/platform instances immediately, but **walker graphs and walker
PIE wait for M1 GREEN**. If a base change is needed, A2 sends a request to A1;
do not add the variable or function to the child. C builds the
projectile/puddle/shooter support and the ranged walkers in parallel.

---

## 1. Read-in order (M0)

Every owner reads:

1. `Docs/EnemyAI.md` §1–2 (locked rules, state model).
2. `Docs/Enemies.md` §3–4 (base variables, functions, event graph).
3. `Docs/EnemyWorkPlan.md` §3–6 (this file: rules, ownership, gates).
4. `Docs/LfsLocking.md` (binary assets cannot merge).

Then read the sections named in your work card in §7. Read
`Docs/EnemyPlacement.md` only when you reach M4 or need a placement answer.

If two documents disagree, **stop and post the conflict** in the status log.
`EnemyAI.md` wins over `Enemies.md`; `EnemyPlacement.md` never overrides either.

---

## 2. Status at the start

**Done and verified**

- All 20 Blueprint shells exist under
  `Content/DontTrustTheLevels/Enemies/Blueprints/`.
- `BP_EnemyBase` has the shared health/damage/death/contact graph.
  `py -3 Scripts\_verify_enemy_base.py` reports **52 PASS / 0 FAIL**.
- `BP_EnemyPlatform` exists and seven auto zones exist in `L_Level_01`.
- `BPI_Killable` is implemented on `BP_EnemyBase`; traps are player-only.

**Built in `BP_EnemyBase` (re-verified from the export + live CDO, 4 Nov 2026)**

- All **13/13** AI functions exist: `PointInPlatformZone`, `PointInPlatformXZ`,
  `FindHomePlatform`, `AdoptPlatform`, `LedgeAhead`, `PatrolStep`,
  `IsPlayerOnHomePlatform`, `IsPlayerInAggroBox`, `ChaseStep`, `UpdateAggro`,
  `ResolveKnockback`, `MeasurePlatformWidth`, `TryRescue`. The asset has **21
  function graphs** in total (`InitEnemy`, `Die`, `RefreshStateFlipbook`,
  `SetFacing`, `ClearIFrames`, `RecoverFromHit`, `PlayStateFlipbook`, …).
- All 25 §4 variables exist with the documented defaults:
  `py -3 Scripts\_check_enemy_ai_vars.py` reports **25 PASS / 0 FAIL** live
  (the 25th, `bAggroOnHit`, landed with the aggro-on-hit change; the two rename
  failures of 27 Oct are gone).
- `Event Tick` is wired, and `ContactBox` exists with the contact chain bound to
  it — the 25 Oct defect report below is resolved.

**Proven in PIE (the three A2 assets inherited from B)**

- `BP_SpikeTurtle` — test 10 PASS · `BP_Ghost` — tests 12–13 PASS ·
  `BP_Bat` — test 14 PASS (`TriggerRadius=1000`, `ChaseSpeed=1000`,
  `KnockbackForce=0`).

**Not built**

- The **M1 walker PIE gate (tests 1–9) is still not logged** — there is no
  `M1 GREEN` line in §10. The base code is present, but walker graphs and walker
  PIE remain blocked until A1 posts that line.
- Every child-specific mechanic. Live CDO check on 4 Nov 2026:
  `BP_Rock1/2/3`, `BP_WoodLog`, `BP_Rhino`, `BP_ToxicSlime` and
  `BP_FloatingSkull` all still hold the **base defaults** (`ChaseSpeed=150`,
  `MoveSpeed=100`, `MaxHealth=3`, `AggroHalfWidth=600`, `AggroHalfHeight=500`,
  `ContactDamage=1`) and declare **zero** own variables, so none of them has
  started. `BP_Snail` now overrides the aggro values (`ChaseSpeed=250`, both
  aggro halves `0`, `bAggroOnHit=true`; saved 5 Nov), but its health, movement
  and snail flipbooks are still on the base defaults (`MaxHealth=3`,
  `MoveSpeed=100`, `IdleFlipbook`/`HitFlipbook`/`DeathFlipbook` unset) — the
  remaining A1b Class Defaults work is still open.
- The projectile/puddle/shooter support graphs.

**Current blockers / cleanup**

- **DONE 24 Oct** — `bEnable` → `bEnabled` in `BP_EnemyPlatform`; live check:
  `bEnabled=true`, `Zone` extent `(50,50,20)`, `NoCollision`, hidden,
  `PatrolInset=80`. The generator alias is kept for compatibility.
- Do not add `MaxWalkSpeed` as a variable; it is a `CharacterMovement` property.
- Remove the duplicate typo variable `KnowbackForce` if it is still present;
  keep `KnockbackForce`.
- This UE 4.27.2 build has **no Python route to create K2 nodes**. Node
  placement, wiring, compilation and PIE are manual editor work. Python may
  create/configure shells and read T3D for verification, not author graphs.
- `BP_Snail` is currently at `(-451, 9, 225)` and does not match an auto marker.
  Do not treat that placement as a valid home-platform test.

---

## 3. Non-negotiable rules

1. **Lock before editing.** Use Git LFS / UE Source Control for every
   `.uasset` and `.umap`; commit and push promptly to release the lock. Never
   co-edit a Blueprint, and never share one working copy/editor between two
   owners.
2. **One movement authority per asset.**
   - Walkers (`Rocks`, `Snail`, `Slime`, `Rhino`, `WoodLog`) use the base
     `Event Tick` → `PatrolStep` / `ChaseStep`. Do **not** add a second movement
     `Event Tick` to a walker.
   - Stationary/flyers (`SpikeTurtle`, `Ghost`, `Bat`, `FloatingSkull`) set
     `bCanMove=false`; their own `Event Tick` / `LaunchCharacter` is the only
     movement. `ChaseSpeed=0` for Turtle/Ghost/Skull; Bat keeps the inherited
     `ChaseSpeed=1000` for `MaxFlySpeed`. This is what stops the shared walker
     loop from also running.
   - `bCanMove` is a shared-AI gate, not a CharacterMovement property. Setting
     it false does not stop `Add Movement Input` or `LaunchCharacter`.
3. **No duplicate variables.** Inherit from `BP_EnemyBase`:
   `bAggro`, `AggroRadius`, `ChaseSpeed`, `MoveSpeed`, `KnockbackForce`,
   `Facing`, all health/contact variables and all three base flipbooks.
   - `BP_Ghost` must not declare `bAggro` or `AggroRadius`.
   - `BP_Bat` must not declare `ChaseSpeed`.
   - `BP_Rhino` must not declare `MoveSpeed`.
   - Child values for inherited variables belong in **Class Defaults**, not in
     a new variable.
4. **Home platform type.** `HomePlatform` should be a `BP_EnemyPlatform` object
   reference. If it is already an `Actor`, retype it or cast once in
   `FindHomePlatform`; do not cast at every use.
5. **Contact damage uses `ContactBox`**, not the blocking capsule. `ContactBox`
   is already on `BP_EnemyBase` with `Pawn=Overlap` and all other channels
   `Ignore`; do not rebuild it in a child.
6. **Compile + save after every graph or function.** A red compile error in a
   child usually means a missing parent member; do not hide it by duplicating
   the member in the child.
7. **Walkers wait for M1.** Until A1 posts the base gate (variables, functions,
   `PatrolStep`/`LedgeAhead`, compile clean, 52 PASS, tests 1–9), do not wire
   `Snail`, `Rocks`, `Slime`, `Rhino` or the final `WoodLog` aggro wiring.
   A1 may prepare Snail unique variables/defaults; A2 may prepare Rock and Skull
   unique variables/defaults, art and static map/platform instances. No walker
   graph or walker PIE before M1. Stationary/flyers (A2) and the
   projectile/puddle/shooter support (C) may start immediately because they do
   not read the walker AI.
8. **Shared bases are single-owner.**
   - A1 only: `BP_EnemyBase`, `BP_EnemyPlatform`, `BP_Snail`.
   - A2 only: `BP_RockBase`, `BP_Rock1/2/3`, `BP_SpikeTurtle`, `BP_Ghost`,
     `BP_Bat`, `BP_FloatingSkull`.
   - C only: `BP_ShooterEnemyBase`, `BP_EnemyProjectile*`, `BP_ToxicPuddle`.
   - A2 never edits a shared base: the four stationary/flyer assets extend the
     base, they do not modify it. A base change is an A1 request.
9. **Level maps are single-owner.** Only A2 edits `L_Level_01` (M1 smoke-test
   staging and M4) and `L_Level_Testing` (A2's scratch PIE map for the
   stationary/flyer assets). A1 and C provide placement coordinates and test
   results; they never save a map. A2 stages and removes the temporary M1 test
   actor at A1's request.
10. **No new base classes, no Behavior Tree, no NavMesh, no C++.** No Pea Plant
    work. No Python graph authoring.
11. **Docs are contract files.** A1 owns edits to `EnemyAI.md`, `Enemies.md` and
    `EnemyPlacement.md`. A2 and C may append to the status log in this file and
    may propose a correction; they must not rewrite a contract to match their
    graph.
12. **Definition of done is per asset**, not "the graph looks finished": see §9.

---

## 4. Ownership map

| Asset | Owner | Depends on | Notes |
|---|---|---|---|
| `BP_EnemyBase` | A1 | — | AI core, M1 |
| `BP_EnemyPlatform` | A1 | — | DONE — `bEnabled=true`, Zone verified |
| `BP_Snail` | A1 | M1 | walker; hit-only aggro (zero box, `bAggroOnHit`) |
| `BP_RockBase` | A2 | M1 | split logic |
| `BP_Rock1/2/3` | A2 | M1, `BP_RockBase` | child defaults + split |
| `BP_SpikeTurtle` | A2 | base health only | DONE (was B) — stationary, no detection |
| `BP_Ghost` | A2 | base health only | DONE (was B) — flyer, own Tick |
| `BP_Bat` | A2 | base health only | DONE (was B) — flyer, own Tick |
| `BP_FloatingSkull` | A2 | base health only | was B — bounce, own `Event Hit`; the only remaining A2 special |
| `BP_EnemyProjectile` | C | — | support |
| `BP_EnemyProjectile_Wood` | C | projectile base | child defaults |
| `BP_ToxicPuddle` | C | — | support |
| `BP_ShooterEnemyBase` | C | — | support |
| `BP_WoodLog` | C | C support + M1 | walker that stops to shoot |
| `BP_ToxicSlime` | C | M1 + puddle | walker; no detection |
| `BP_Rhino` | C | M1 | walker charger |
| `BP_PeaPlant` | nobody | — | unused; do not place or extend |
| `BP_EnemyProjectile_Pea` | nobody | — | unused shell |
| `L_Level_01` | A2 | all behavior gates + A1 M1 smoke test | M1 staging + M4 only |
| `L_Level_Testing` | A2 | — | A2 scratch PIE map (was B's); never a shipped-level edit |

If a new asset is needed, add it to this table before creating it. Do not create
a second “base” or a manager actor to avoid a dependency. Exact lock paths are
in §4.1; that list is the conflict boundary.

### 4.1 Exact files to lock (no ambiguity)

All enemy Blueprints live in
`Content/DontTrustTheLevels/Enemies/Blueprints/`. Lock the exact `.uasset`
file, never a folder; use the paths below verbatim with `git lfs lock`.

**Owner A1 — shared base + Snail**

- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_EnemyBase.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_EnemyPlatform.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Snail.uasset`
- Docs: `Docs/EnemyAI.md`, `Docs/Enemies.md`, `Docs/EnemyPlacement.md`,
  `Docs/EnemyWorkPlan.md` (contract edits)

**Owner A2 — rocks + stationary/flyers + level** (absorbed all of Owner B on
4 Nov 2026)

- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_RockBase.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Rock1.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Rock2.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Rock3.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_FloatingSkull.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_SpikeTurtle.uasset` —
  **DONE; regression only**
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Ghost.uasset` —
  **DONE; regression only**
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Bat.uasset` —
  **DONE; regression only**
- `Content/DontTrustTheLevels/Levels/L_Level_01.umap` — **M1 test staging and M4 only**
- `Content/DontTrustTheLevels/Levels/L_Level_Testing.umap` — A2 scratch PIE map
  (formerly B's; never a shipped-level edit)
- May append only to the status log in `Docs/EnemyWorkPlan.md`; request contract
  changes from A1

**Owner C**

- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_EnemyProjectile.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_EnemyProjectile_Wood.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_ToxicPuddle.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_ShooterEnemyBase.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_WoodLog.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_ToxicSlime.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Rhino.uasset`
- May append only to the status log in `Docs/EnemyWorkPlan.md`

**Nobody edits**

- `BP_PeaPlant.uasset` and `BP_EnemyProjectile_Pea.uasset` — unused shells.
- `L_Level_00.umap`, `L_Level_02.umap`, `L_Menu.umap` — not part of this work.
- Another owner's file, even for a one-line default change. Send a request
  instead.
- `Saved/`, `Intermediate/`, `DerivedDataCache/`, or probe dumps.

If the file is not listed for you, you do not own it. If a needed asset is
missing, add it to §4 first and tell A1 before creating it.

### 4.2 A1/A2 parallel boundary

This split is conflict-free only while both owners stay on their side of the
boundary:

| A1 may edit/save | A2 may edit/save |
|---|---|
| `BP_EnemyBase`, `BP_EnemyPlatform`, `BP_Snail` | `BP_RockBase`, `BP_Rock1/2/3`, `BP_FloatingSkull`, `BP_SpikeTurtle`, `BP_Ghost`, `BP_Bat` |
| contract docs in §4.1 | `L_Level_01`, `L_Level_Testing` |
| — | status-log lines only; request contract changes from A1 |

- A1 never saves `L_Level_01` or a Rock child. A1 may PIE-test the map after
  A2 saves a test setup, but must not save the map.
- A2 never opens `BP_EnemyBase`, `BP_EnemyPlatform` or `BP_Snail` for saving. If
  the base, platform or Snail class needs a change, A2 posts a request to A1.
- A2 stages the map instance of the temporary M1 smoke-test actor (`BP_Rock1` on
  P_02 or `BP_Snail` on P_00), commits/pushes the map and releases the lock so A1
  can pull it. A2 never edits the Snail asset. A1 runs PIE without saving; A2
  removes the actor after M1 and pushes the cleanup. A1 never saves the map.
- A1 may prepare Snail variables/defaults/art; A2 may prepare Rock and Skull
  variables/defaults/art and static map/platform placement. Walker graphs and
  walker PIE wait for `M1 GREEN`.
- `BP_EnemyPlatform` is frozen for A2 placement after M1. If A1 must change the
  class, A2 re-saves the affected map instances and re-runs the walker smoke test.

No file in the left column overlaps a file in the right column. A Git LFS lock
conflict means one of these rules was broken, not that the split is wrong.

A1's post-M1 work is Snail; A2's is Skull, then Rocks, then the two maps. A2 now
carries both the M2 specials and the M4 map block, so the order in §6 is a hard
sequence for A2, not a menu: finish `BP_FloatingSkull` before opening
`L_Level_01`, and hand Rock placement to M4 after the Rocks compile. A1 hands
over exact placement coordinates and PIE results but must not save a map.

---

## 5. Dependency graph

```text
M0  all owners read the docs (no edits)
     |
     +-- A1: M1  BP_EnemyBase AI core gate ---------------------+
     |           (blocks every walker)                          |
     |                                                          |
     +-- A2: M2  FloatingSkull                                  |
     |          (Turtle/Ghost/Bat already DONE - regression only)|
     |          (no base-AI dependency)                         |
     |                                                          |
     +-- A2: prep Rock vars/defaults + static map placement     |
     |          (no walker graph or walker PIE before M1)       |
     |                                                          |
     +-- C: M2b Projectile -> Puddle -> Shooter -> WoodLog      |
                (support; WoodLog final aggro waits for M1)      |
                                                                 |
     M1 gate ----------------------------------------------------+
     |
     +-- A1: M3a Snail
     +-- A2: M3b Rocks
     +-- C: M3c Rhino -> Toxic Slime
     |
     M4  integration, placement, full PIE matrix
         (A2 owns both maps; A1 owns base verifier + contract docs)
```

M1 is the only hard gate. A1 may prep Snail and A2 may do Rock/map preparation
while A1 builds the base, but walker graphs and walker PIE wait for M1 GREEN.
A2's specials (only `BP_FloatingSkull` is left) and C's
projectile/puddle/shooter work do not read the walker AI and may run
immediately. C may build the Wood Log defaults and firing graph early, but must
not wire or PIE-test its aggro/patrol until M1 is green.

---

## 6. Milestones and gates

### M0 — Read-in (all owners; no edits)

- Read §1 and your work card.
- Confirm your asset list and locks.
- **Comprehension check:** ask your AI to restate its slot, its exact §4.1
  files, its first asset, its dependency gate, its first three tasks and its
  stop conditions. If it cannot, it has not read enough; do not let it edit.
- Post one line in the status log: `M0 done`, your slot, and the first asset.
- If you find a doc conflict, post it before touching an asset.

### M1 — `BP_EnemyBase` AI core gate (A1; blocks walkers)

**Read:** `EnemyAI.md` §3–7 and §10; `Enemies.md` §3–4.

**Work**

1. **DONE 24 Oct** — rename `bEnable` → `bEnabled` in `BP_EnemyPlatform`,
   compile and save. Live check: `bEnabled=true`, `Zone` `NoCollision`/hidden.
2. **DONE 4 Nov 2026; re-verified 5 Nov** — the §4 variables exist;
   `_check_enemy_ai_vars.py` = **25 PASS / 0 FAIL**. `MoveSpeed` was never
   duplicated, `HomePlatform` is typed, `KnowbackForce` is gone and `MaxWalkSpeed`
   was not added as a variable. If a step below still looks open, trust this line:
   the asset was re-read.
3. **DONE 4 Nov 2026** — all four function batches exist (13/13 AI functions,
   21 function graphs in the asset):
   - `PointInPlatformZone`, `PointInPlatformXZ`, `FindHomePlatform`,
     `AdoptPlatform`.
   - `LedgeAhead`, `PatrolStep`.
   - `IsPlayerOnHomePlatform`, `IsPlayerInAggroBox`, `ChaseStep`, `UpdateAggro`.
   - `ResolveKnockback`, `MeasurePlatformWidth`, `TryRescue`.
4. **Verify in PIE** — `BeginPlay` → `FindHomePlatform`; `Landed` →
   `ResolveKnockback`; `Tick` → the state loop (wired); `AnyDamage` sets
   `bWasKnockedBack` before `LaunchCharacter`.
5. The `Event Tick` gate must be:
   `bIsDead OR bStranded OR NOT bCanMove` → return, then
   `bWasKnockedBack` → return, then `ChaseSpeed <= 0` → `PatrolStep` and return.
   This is what makes stationary/flyers safe and Snail/Slime patrol-only.
6. `UpdateAggro` must skip to `PatrolStep` when `ChaseSpeed <= 0`; do not let a
   no-detection walker set `bAggro`.
7. **DONE 5 Nov 2026, A1** — the aggro-on-hit change (`bAggroOnHit`, the existing
   `DeAggroTime` reused as the post-hit window, `Reachable` formula) from §7 `A1`
   and §13 landed before the Rock/WoodLog/Snail CDO flips. `UpdateAggro` is 54
   nodes with the three corrected links, and `_verify_enemy_base.py` now fails if
   any of the three old links returns.

**M1 acceptance gate**

- Parent and every compiled child have no red errors.
- `py -3 Scripts\_verify_enemy_base.py` holds **52 PASS / 0 FAIL**.
- PIE tests 1–9 from `EnemyAI.md` §11 pass on a temporary `BP_Rock1` placed on
  P_02 (z ≈ `506.25`) or `BP_Snail` on P_00 (z ≈ `875`). A2 stages, commits and
  pushes the test setup, then A1 pulls and runs PIE. A1 never saves the map; A2
  removes the test actor after M1. Do not save level tuning yet.
- Specifically verify: patrol edge turns, same-platform-only aggro, de-aggro,
  knock-off platform adoption, stair stranding/rescue.
- Commit + push, then post `M1 GREEN` with the verifier output. Only then may
  A1 start Snail, A2 start Rocks and C start Slime/Rhino/final Wood Log aggro.

Existing auto-zone surfaces in `L_Level_01` (world X / Z / width):
P_00 `x=-400, z=800, w=800` · P_01 `x=950, z=600, w=500` ·
P_02 `x=-800, z=400, w=800` · P_03 `x=350, z=400, w=500` ·
P_04 `x=-1750, z=100, w=300` · P_05 `x=-1300, z=0, w=600` ·
P_06 `x=550, z=0, w=2700`. Use these for the M1 smoke test; add more zones
only in M4.

### M2 — Independent specials (A2; only the Skull is left)

Order: ~~`BP_SpikeTurtle` (warm-up) → `BP_Ghost` (highest risk) → `BP_Bat`~~
(these three are **DONE**, see §10) → **`BP_FloatingSkull`** (remaining).

- None of these use `PatrolStep`, `LedgeAhead`, `IsPlayerOnHomePlatform` or the
  walker aggro loop.
- Set `bCanMove=false` on all four. `ChaseSpeed=0` for Turtle/Ghost/Skull;
  Bat keeps `ChaseSpeed=1000` for `MaxFlySpeed`. Turtle and Skull have no child
  movement Tick; Ghost and Bat use their own Tick.
- Compile + save after each graph; PIE each asset before moving to the next.
- New to A2: do **not** rebuild the three DONE assets. Touching them is a
  regression risk with no upside; only open one if a PIE retest fails, and then
  treat it as a defect, not a task.

**M2 acceptance:** nothing needs re-proving on Turtle/Ghost/Bat — tests 10, 12,
13 and 14 are already PASS and stay as regressions. The open item is Skull's
extended test from `Enemies.md` §7.3, plus no base-verifier regression.

### M2b — Support graphs (C; can start now)

Order: `BP_EnemyProjectile` (+ `_Wood`) → `BP_ToxicPuddle` →
`BP_ShooterEnemyBase` → `BP_WoodLog` defaults/fire graph.

- `BP_EnemyProjectile_Pea` is untouched.
- `BP_ShooterEnemyBase` is C-only. `TryFire` sets `bCanShoot=false` and
  `bCanMove=false` before spawning; `EndAttack` restores both.
- Wood Log's patrol/aggro is not wired until M1. Building its defaults and
  horizontal `TryFire` early is allowed.

**M2b acceptance:** projectile hits walls, ignores its shooter, self-destructs
at 5 s and calls `Kill` on the player; puddle self-destructs at 3 s and kills
only the player; shooter base compiles with no red errors.

### M3 — Walkers (after M1)

**A1:** `BP_Snail`.

**A2:** `BP_RockBase`/`BP_Rock1/2/3` — only after `BP_FloatingSkull` is done in
M2, because A2 is now single-threaded across both milestones.

**C:** `BP_Rhino` → `BP_ToxicSlime` → finish `BP_WoodLog` aggro/patrol.

- A walker must not add its own movement Tick. Use base `PatrolStep`,
  `ChaseStep` and `UpdateAggro`; override only the state-specific parts.
- Toxic Slime sets `ChaseSpeed=0` (no detection). Rocks, Rhino and Wood Log set
  a positive `ChaseSpeed`. Snail is the §13 exception: `ChaseSpeed=250` with
  `AggroHalfWidth=0` / `AggroHalfHeight=0` and `bAggroOnHit=true`, so it only
  reacts to being shot.
- Snail's shell uses the same base `PatrolStep` with `MoveSpeed=ShellSpeed`;
  do not add the old shell Tick.
- Wood Log overrides `ChaseStep` to stand and shoot; it does not chase.
- Rhino overrides `UpdateAggro` only to maintain `bCharging` after calling
  `Parent: UpdateAggro`; detection itself stays in the base.

**M3 acceptance:** tests 11, 15, 16 plus the Snail/Toxic Slime checks in
`Enemies.md` §7.3; split pieces adopt their landing platform; shell stays on
platform; Rhino dies on the 4th wall hit.

### M4 — Integration, placement and tuning (all; A2 owns both maps, A1 owns verifier/docs)

- A2 places the test enemies and any additional `BP_EnemyPlatform` zones in
  `L_Level_01`; A1 and C report coordinates and do not save the map.
- A2 coordinates the full `EnemyAI.md` §11 matrix (1–16) plus the extended
  checks in `Enemies.md` §7.3; each owner runs its own asset's PIE checks. A2
  also re-runs tests 10/12/13/14 as regressions on the three inherited assets.
- Tune `AggroHalfWidth/Height`, `ChaseSpeed`, `DeAggroTime`, `RescueRadius`,
  `MinPatrolWidth` and per-enemy speeds in Class Defaults, not in duplicated
  child variables. A1 owns base/platform/Snail defaults; A2 owns Rock + Skull
  defaults.
- A1 re-runs `_verify_enemy_base.py`; hold **52 PASS / 0 FAIL**. A1 also owns
  the aggro-on-hit contract change (`bAggroOnHit`, with `DeAggroTime` reused as
  the post-hit window); it is landed in the base, so the
  Rock/WoodLog/Snail CDO flips can proceed.
- A1 commits contract docs + Snail; A2 commits both maps + Rocks + Skull; all
  owners clean probe files and release their locks.

---

## 7. Work cards

Each card is the assignment. The card tells you **what to build and how to
prove it**; the linked sections contain the exact pin-level recipes. Do not
invent a third source.

Cards are numbered by asset group, not grouped by owner, so use this index:

| Owner | Cards | State on 4 Nov 2026 |
|---|---|---|
| **A1** | `A1` (`BP_EnemyBase`), `A1b` (`BP_Snail`) | base code complete and verified (13/13 functions, 25/25 vars, 45 PASS); `UpdateAggro` aggro-on-hit landed; Snail aggro CDO set (80 / 0 / 0, `bAggroOnHit=true`); next = PIE 1–9 + remaining Snail Class Defaults; M1 PIE not logged |
| **A2** | `A2a` (Rocks), `A2b` (Turtle), `A2c` (Ghost), `A2d` (Bat), `A2e` (Skull) | 3 of 5 done (Turtle, Ghost, Bat); Skull + Rocks open |
| **C** | `C1`–`C6` | nothing started |

Owner B has no cards; `A2b`–`A2e` are the transferred ones.

### A1 — `BP_EnemyBase` AI core (Owner A1)

**Read:** `EnemyAI.md` §3–7, §10; `Enemies.md` §3–4.

**Depends:** none. **Blocks:** every walker.

**Scope:** edit only `BP_EnemyBase`, `BP_EnemyPlatform`, `BP_Snail` and the
contract docs. Never save `L_Level_01`; A2 stages/removes the M1 test actor.

**Tasks**

- [x] **DONE 24 Oct** — rename `bEnable` → `bEnabled` in `BP_EnemyPlatform`;
      compile/save. Live check: `bEnabled=true`, `Zone` extent `(50,50,20)`,
      `NoCollision`, hidden.
- [x] Add the new §4 variables, including typed `HomePlatform`; `MoveSpeed`
      already exists; remove `KnowbackForce`; do not add `MaxWalkSpeed`.
      **DONE 4 Nov 2026; re-verified 5 Nov** — all 25 §4 variables exist with the
      documented defaults; `Scripts\_check_enemy_ai_vars.py` = **25 PASS / 0 FAIL**
      (both October renames landed; `bAggroOnHit` is the 25th).
- [x] Build `PointInPlatformZone`, `PointInPlatformXZ`, `FindHomePlatform`,
      `AdoptPlatform`.
- [x] Build `LedgeAhead`, `PatrolStep`.
- [x] Build `IsPlayerOnHomePlatform`, `IsPlayerInAggroBox`, `ChaseStep`,
      `UpdateAggro`. **DONE 4 Nov 2026** — all four function graphs exist
      (21 function graphs in the asset, 13/13 AI functions).
- [x] Build `ResolveKnockback`, `MeasurePlatformWidth`, `TryRescue`.
      **DONE 4 Nov 2026.**
- [x] Wire `BeginPlay`, `Landed`, `Event Tick`, and the `AnyDamage`
      `bWasKnockedBack` flag. **`Event Tick` is a wired event node.**
- [x] **DONE 5 Nov 2026 — aggro on hit** (`EnemyAI.md` §6.2/§6.3). `bAggroOnHit`
      (Boolean, `false`) exists and `UpdateAggro` is 54 nodes; the hit term reuses
      `DeAggroTime` and skips the same-platform/Z gate. Live CDO flips landed on
      `BP_Rock1/2/3`, `BP_WoodLog` and `BP_Snail`. `BP_Bat` needs its own
      `RefreshStateFlipbook` hit branch because it never runs the walker loop.
- [x] **DONE 7 Nov 2026 — `LaunchCharacter` Z override.** The `AnyDamage` launch
      now has `bZOverride = true`, so a zero `KnockbackForce` sends a zero vector
      and `HandlePendingLaunch()` returns early. `BP_Bat` (the only
      `KnockbackForce=0` child) keeps `MOVE_Flying` / `MaxFlySpeed` after a hit;
      grounded walkers are unchanged (`Vz ≈ 0`). Evidence: §10 row of 7 Nov,
      `Scripts/_check_bat_hit_knockback.py` → `PASS (A)`,
      `_verify_enemy_base.py` 52 PASS / 0 FAIL.
- [ ] **Gate:** verify the Top gate
      (`bIsDead OR bStranded OR NOT bCanMove` → return; `bWasKnockedBack` →
      return; `ChaseSpeed <= 0` → `PatrolStep` → return) in PIE with tests 1–9.
      All three AI halves now exist, so this is a verification task, not a build
      task. Run it and post `M1 GREEN`.

**Done when:** `_verify_enemy_base.py` = 52 PASS / 0 FAIL; tests 1–9 pass;
compile clean; committed; `M1 GREEN` posted.

---

### A2b — `BP_SpikeTurtle` (Owner A2 — **DONE**, transferred from B)

**Read:** `EnemyAI.md` §8.1; `Enemies.md` §6.1; `EnemyPlacement.md` §4.1.
**Depends:** base health/contact only. **No base AI.**

**Status: DONE** — test 10 PASS (§10 status log, 25 Oct 2026), including the
contact kill after the base `ContactBox` fix. Two open rulings were inherited
from B's last resave and are **still pending A1**: the turtle capsule ended at
`Pawn=Block`, and the `ToggleIdle` timer in the card below was removed from the
graph. Neither breaks test 10, so do not "fix" them silently — A1 rules, then
this card is synced to the asset. Do not re-derive the graph.

**Tasks**

- [ ] Add only the eight child variables: `bSpikesOut`, `SpikeInterval`,
      `SpikeChangeTime`, `SpikesOutFlipbook`, `SpikesInFlipbook`,
      `IdleFlipbookA`, `IdleFlipbookB`, `bIdleAlt`.
- [ ] Class Defaults: `bCanMove=false`, `ChaseSpeed=0`, `bUseHealth=false`,
      `bInvulnerable=true`, `ContactDamage=1`, `MaxHealth=3`, turtle flipbooks.
- [ ] `BeginPlay` → `InitEnemy`; loop timers `SpikeCycle` (`SpikeInterval`) and
      `ToggleIdle` (`1.4`).
- [ ] `SpikeCycle` → toggle `bSpikesOut`; play the in/out flipbook; start
      `FinishSpikeChange` (`SpikeChangeTime`, one-shot).
- [ ] `FinishSpikeChange` → `bDealContactDamage = bSpikesOut`;
      `ContactDamage=1.0`; `RefreshStateFlipbook`.
- [ ] `ToggleIdle` → flip `bIdleAlt`; `RefreshStateFlipbook`.
- [ ] Override `RefreshStateFlipbook` to choose the spike/idle flipbook.

**Done when:** test 10 passes: stationary, no detection, no patrol Tick, bullets
and `Kill` do nothing, contact only while spikes are out, `KillVolume` destroys.

**Do not:** add a patrol Tick, detection, `bCanMove=true`, or health damage.

---

### A2c — `BP_Ghost` (Owner A2 — **DONE**, transferred from B)

**Read:** `EnemyAI.md` §8.4; `Enemies.md` §6.4; `EnemyPlacement.md` §4.4.
**Depends:** base health/contact only. **No base AI.**

**Status: DONE** — tests 12–13 PASS (§10, 26 Oct 2026): 550-sphere trigger,
through-wall chase, visible/hidden loop, 2 hits, no de-aggro. **Open item, A2:**
Ghost was built before M1, so it declares TEMP-M1 locals `bAggro`,
`AggroRadius` and `ChaseSpeed` in the child. The base now owns all three, so
those are shadow variables — delete them, inherit, and retest 12–13. Also keep
the native-left art fix: the Ghost sprite faces left, so the `SetFacing` input is
negated inside the chase.

**Tasks**

- [ ] Add only the unique variables: `bInvisible`, `VisibleTime`,
      `InvisibleTime`, `FadeTime`, `AppearFlipbook`, `DisappearFlipbook`.
      **Do not** declare `bAggro` or `AggroRadius`; inherit them.
- [ ] Class Defaults: `bCanMove=false`, `ChaseSpeed=0`, `AggroRadius=550`,
      `MaxHealth=2`, `MoveSpeed=80`, `ContactDamage=1`, ghost flipbooks.
- [ ] `BeginPlay` (child addition): `InitEnemy`; `bInvisible=true`;
      `Sprite0` hidden; `CollisionCylinder` NoCollision; `ContactBox` off;
      `bInvulnerable=true`; `bDealContactDamage=false`; `bAggro=false`.
- [ ] Own `Event Tick`: when `NOT bAggro`, valid player and
      `VSize(Player - Self)` in the XZ plane `<= AggroRadius` → `StartAggro`.
      Once aggroed, move directly at the player in X/Z.
- [ ] `StartAggro`: visible sprite, collision on with `WorldStatic=Ignore`,
      `ContactBox` on, vulnerable, contact on, play `AppearFlipbook`, start
      `StartDisappear` (`VisibleTime`).
- [ ] Build the visible/hidden loop exactly as `Enemies.md` §6.4:
      `StartDisappear`, `BecomeInvisible`, `StartAppear`, `BecomeVisible`.
- [ ] Hidden phase turns off **both** the capsule and `ContactBox`; visible
      phase restores both. No `bInvulnerableWhileInvisible` variable.
- [ ] Override `RefreshStateFlipbook`: hidden = do nothing; visible = idle loop.

**Done when:** tests 12–13 pass: hidden = no collision/contact/chase; trigger
= visible phase, through-wall chase, loop forever, no de-aggro.

**Do not:** add base walker Tick behavior, set `WorldStatic=Block`, or add a
de-aggro branch.

---

### A2d — `BP_Bat` (Owner A2 — **DONE**, transferred from B)

**Read:** `EnemyAI.md` §8.8; `Enemies.md` §6.8; `EnemyPlacement.md` §4.8.
**Depends:** base health/contact only. **No base AI.**

**Status: DONE (5 Nov 2026 — regression fixed).** Test 14 passed on 27 Oct.
All three playtest bugs are verified fixed in PIE: the live
`RefreshStateFlipbook` has the 13-node hit branch from
`Scripts/_bp_bat_hit_aggro_only.txt` plus the
`Set MaxFlySpeed = ChaseSpeed` write, and the EventGraph `HangIdle` custom event
is gated on `bTriggered`. The staged 17-node
`Scripts/_bp_bat_refresh_modified_v2.txt` remains available for a clean
re-paste (it also contains the hit-path `K2_ClearTimer("HangIdle")`). Live CDO
otherwise unchanged: `TriggerRadius=1000`, `ChaseSpeed=1000`,
`KnockbackForce=0`, `MaxAcceleration=8192`.

**Follow-up (7 Nov 2026):** the remaining "slow / invisible after a hit"
playtest report was not a graph bug — the saved asset was re-verified by a
headless T3D export and CDO readback (hit branch, `HangIdle` gate and
`MaxFlySpeed` write all intact). The **Level 1 instance** was placed at
`Y=-100` while the terrain plane (`TM_Background`, `collision_thickness=200`,
BlockAll) is at `Y=0`; its sprite rendered behind the terrain and its capsule
was embedded in the collision slab. The instance now sits at `Y=0`. Keep
flyers on the terrain plane (`EnemyPlacement.md` §2).

**Root cause of the remaining slowdown (7 Nov 2026, second pass):** the `Y` fix
removed the *invisible* sprite, but the Bat still crawled after a hit. The shared
`AnyDamage` knockback called `LaunchCharacter(..., bZOverride=false)`, and that
flag makes the launch vector inherit the Bat's own Z velocity, so
`KnockbackForce=0` still triggers `HandlePendingLaunch() ->
SetMovementMode(Falling)`. In `Falling` the cap is
`MaxWalkSpeed = MoveSpeed = 100` (written by the same handler) and only
`AirControl`-scaled X/Y input applies, so `MaxFlySpeed=1000` never matters.
`bZOverride=false` is fine for grounded walkers; `BP_Bat` is the only CDO with
`KnockbackForce=0` (every other enemy is `200`). Fix (either one):
`BP_EnemyBase.LaunchCharacter → Z Override` ✓ (root cause, A1) or a `BP_Bat`
Tick node `SetMovementMode(Flying)` before `Bat Tick Logic` (bat only, pre-wired
in `Scripts/_bp_bat_flying_guard_paste.txt`). **Applied 7 Nov 2026 (A1):** the
base pin is `true` and saved; `Scripts/_check_bat_hit_knockback.py` →
`RESULT: PASS (A: bZOverride=true)`; `_verify_enemy_base.py`
45 PASS / 0 FAIL. The Option-B guard is not in the asset and is not needed.
PIE 7/8 (walker knockback + landing/adoption) and 14 (Bat) still to re-run.

**Tasks**

- [ ] Add only the unique variables: `bTriggered`, `bChasing`,
      `TriggerRadius`, `CeilingInFlipbook`, `CeilingOutFlipbook`,
      `FlyingFlipbook`, `HangingFlipbook`. **Do not** declare `ChaseSpeed`;
      inherit it and set it to `1000` in Class Defaults.
- [ ] Class Defaults: `bCanMove=false`, `ChaseSpeed=1000`, `TriggerRadius=1000`,
      `MaxHealth=2`, `ContactDamage=1`, bat flipbooks.
- [ ] `BeginPlay`: `InitEnemy`; `bDealContactDamage=false`; play
      `CeilingInFlipbook`; start `HangIdle` (`0.6`; the callback is gated on
      `bTriggered`, or use `0.3` with the timer-clear alternative).
- [ ] `HangIdle` → Branch `bTriggered` (preferred: false → loop
      `HangingFlipbook`, true → return); or keep unconditional play with the
      `0.3 s` timer plus `K2_ClearTimer("HangIdle")` on the hit chain.
- [ ] Own `Event Tick`: trigger only when the player is valid and within the
      `1000` sphere; set `bTriggered=true`, contact on, play `CeilingOutFlipbook`,
      start `StartChase` (`0.5`).
- [ ] `StartChase` → `bChasing=true`; `MaxFlySpeed=ChaseSpeed`; loop
      `FlyingFlipbook`.
- [ ] Chase step: direct X/Z `Add Movement Input`; keep collision with walls
      and floors. No de-aggro.
- [ ] Override `RefreshStateFlipbook`: flying while `bChasing`, hanging
      otherwise.

**Done when:** test 14 passes; two hits kill it; contact only after trigger;
it collides with walls/floors and never de-aggros.

**Do not:** set `WorldStatic=Ignore` (that is Ghost-only) or add pathfinding.

---

### A2e — `BP_FloatingSkull` (Owner A2 — **NOT STARTED**, transferred from B)

**Read:** `EnemyAI.md` §8.7; `Enemies.md` §6.7; `EnemyPlacement.md` §4.7.
**Depends:** base health/contact only. **No base AI.**

**Status: NOT STARTED (4 Nov 2026).** Live CDO still holds every base default
(`ChaseSpeed=150`, `MoveSpeed=100`, `MaxHealth=3`, `ContactDamage=1`, 600×500
aggro box) and the asset declares **zero** own variables — it is an empty
template with `UserConstructionScript` → `Parent:`. This is the only A2 special
left, and it is the first A2 task in M2.

**Tasks**

- [ ] Add only the unique variables: `bPoweredOn`, `OnIdleFlipbook`,
      `OffIdleFlipbook`, `HitWallFlipbookA`, `HitWallFlipbookB`,
      `bUseWallAlternate`, `BounceSpeed`.
- [ ] Class Defaults: `bCanMove=false`, `ChaseSpeed=0`, `MaxHealth=2`,
      `ContactDamage=1`, `MoveSpeed=300`, skull flipbooks.
- [ ] `BeginPlay`: `InitEnemy`; `bPoweredOn=true`; `bInvulnerable=true`;
      `bDealContactDamage=true`; play `OnIdleFlipbook`; launch
      `(Facing * BounceSpeed, 0, BounceSpeed * 0.5)` with XY/Z override.
- [ ] Own `Event Hit`: ignore non-wall/floor normals; play alternating
      `HitWallFlipbookA/B`; `TogglePower`; `BackToSkullIdle` (`0.35`);
      reflect the X/Z velocity through `LaunchCharacter`.
- [ ] `TogglePower`: flip `bPoweredOn`; `bInvulnerable=bPoweredOn`;
      `bDealContactDamage=bPoweredOn`; `RefreshStateFlipbook`.
- [ ] Override `RefreshStateFlipbook`: ON idle vs OFF idle.

**Done when:** ON ignores bullets and kills on contact; OFF is harmless and
shootable; wall/floor hit toggles; no detection/chase; no gravity; pit
`KillVolume` destroys it.

**Do not:** add a patrol Tick or a platform zone; it is a flying hazard.

---

### C1 — `BP_EnemyProjectile` + `BP_EnemyProjectile_Wood` (Owner C)

**Read:** `Enemies.md` §5.2 and §5.3.
**Depends:** none.

**Tasks**

- [ ] Add `SphereCollision` (radius `8`, `BlockAllDynamic`, generate hit
      events) and `ProjectileMovement` (initial/max speed `0`, gravity `0`,
      no bounce).
- [ ] Add `Speed=900`, `Damage=1`, `Direction=(1,0,0)`, `Shooter` (Actor).
- [ ] `InitProjectile(Direction, Speed, Damage, Shooter)` sets the four values
      and `Set Velocity = Direction * Speed`.
- [ ] `BeginPlay` → `Set Life Span(5.0)`; apply velocity if `Speed` is set.
- [ ] `On Component Hit (SphereCollision)`: ignore `Shooter`; if other actor is
      the player and implements `BPI_Killable`, call `Kill` then `Destroy Actor`;
      otherwise `Destroy Actor` for walls/floors.
- [ ] Set `BP_EnemyProjectile_Wood` defaults; leave `_Pea` untouched.

**Done when:** projectile hits a wall and destroys itself, never self-hits,
expires at 5 s, and kills the player through `BPI_Killable`.

**Do not:** use `ApplyPointDamage` on the player (the player has no health).

---

### C2 — `BP_ToxicPuddle` (Owner C)

**Read:** `Enemies.md` §5.4.
**Depends:** none.

**Tasks**

- [ ] Add `ToxicBox` (`BoxComponent`, extent `(100,50,20)`,
      `OverlapAllDynamic`, generate overlaps).
- [ ] Keep `InitialLifeSpan=3.0`.
- [ ] `Event ActorBeginOverlap`: if `OtherActor == Get Player Character(0)` and
      it implements `BPI_Killable`, call `Kill`.
- [ ] Optional 0.5 s repeated damage while standing; clear timer on end overlap.
      This is not required for the one-hit player.

**Done when:** puddle disappears at 3 s; player dies on contact; enemies are
unaffected; no graph in the slime is needed for the lifetime.

---

### C3 — `BP_ShooterEnemyBase` (Owner C)

**Read:** `Enemies.md` §5.1 and §5.3.
**Depends:** C1.

**Tasks**

- [ ] Add `ProjectileClass`, `FireInterval`, `NextFireTime`, `MuzzleOffset`,
      `ProjectileSpeed`, `ProjectileDamage`, `AttackFlipbook`, `bCanShoot`,
      `bRequireLineOfSight`.
- [ ] `BeginPlay` → `InitShooter`: `InitEnemy`; set `NextFireTime`; loop
      `TryFire` every `0.2 s`.
- [ ] `TryFire`: return if dead, `NOT bCanShoot`, or before `NextFireTime`;
      require a valid player; face the player; play `AttackFlipbook`; set
      `bCanShoot=false` and `bCanMove=false`; spawn the projectile at the
      muzzle with `(Facing,0,0)` direction; set `NextFireTime`; start
      `EndAttack` (`0.5 s`).
- [ ] `EndAttack` → `bCanShoot=true`, `bCanMove=true`, `RefreshStateFlipbook`.

**Done when:** Wood Log compiles and fires; no Pea Plant work; no self-hit.

---

### C4 — `BP_WoodLog` (Owner C)

**Read:** `EnemyAI.md` §8.9; `Enemies.md` §5.3; `EnemyPlacement.md` §4.9.
**Depends:** C3 + M1. **Allowed early:** defaults and `TryFire` graph.
**Status (5 Nov 2026):** `bAggroOnHit=true` is live and verified; the rest of C4
(health/speeds/flipbooks/`TryFire` verification) is still open.

**Tasks**

- [ ] Class Defaults: `ProjectileClass=BP_EnemyProjectile_Wood`,
      `FireInterval=2.5`, `MuzzleOffset=(90,0,10)`,
      `AttackFlipbook=FLB_Trunk_Attack`, `MaxHealth=3`, `MoveSpeed=90`,
      `ChaseSpeed=90`, `AggroHalfWidth=1400`, `AggroHalfHeight=500`,
      `DeAggroTime=2.0`.
- [ ] Do not add a second `BeginPlay`; the shooter base starts the fire timer.
- [ ] Override `ChaseStep` to **stand and shoot**: face the player, do not move
      toward them, keep `bAggro` from the base.
- [ ] `TryFire` from C3 already gates on `bAggro`; verify it fires only
      horizontally and only inside the rectangle.
- [ ] On de-aggro, `EndAttack` restores movement; base `PatrolStep` resumes.
- [ ] Override `RefreshStateFlipbook`: attack flipbook while firing,
      run while moving, idle otherwise.

**Done when:** test 16 passes: stops inside `1400×500`, fires only
horizontally, de-aggros after `2 s`, resumes patrol, no vertical aim.

**Do not:** chase around the platform, fire at any range, or add a Pea Plant.

---

### A1b — `BP_Snail` (Owner A1)

**Read:** `EnemyAI.md` §8.3; `Enemies.md` §6.3; `EnemyPlacement.md` §4.3.
**Depends:** M1. No detection.

**Parallel prep:** unique variables, Class Defaults and art may be prepared now;
the graph tasks below wait for `M1 GREEN`.

**Status: NOT STARTED (4 Nov 2026).** Live CDO still holds the base defaults
(`ChaseSpeed=150`, `MoveSpeed=100`, `MaxHealth=3`, `ContactDamage=1`), the asset
declares zero own variables, and the instance sits at `(-451, 9, 225)` off every
auto marker. **The aggro part is fixed (5 Nov, retuned 7 Nov):** the Snail overrides
`ChaseSpeed=250` (was `80`), `AggroHalfWidth=0`, `AggroHalfHeight=0` and
`bAggroOnHit=true` — hit-only aggro, patrol otherwise. No proximity aggro is
wanted: a player standing in front of a snail is ignored until it is shot. The
remaining health, movement and flipbook defaults are still base values and are
tracked below. The CDO flip shipped in the same commit as the base change.

**Tasks**

- [ ] Add only the unique variables: `bShellPhase`, `ShellSpeed`,
      `ShellContactDamage`, `ShellLifetime`, `ShellIdleFlipbook`,
      `ShellWallHitFlipbook`, `ShellTopHitFlipbook`, `WithoutShellFlipbook`.
- [x] **DONE 5 Nov 2026 — Class Defaults (aggro only):** `ChaseSpeed=80`
      (raised to `250` on 7 Nov — §10),
      `AggroHalfWidth=0`, `AggroHalfHeight=0`, `bAggroOnHit=true` (§13, locked
      4 Nov). Saved on `BP_Snail` and re-read from the live CDO/spawned instance.
- [ ] Class Defaults (remaining A1b): `MaxHealth=2`, `MoveSpeed=50`,
      `ContactDamage=1`, snail flipbooks. These still inherit the base values
      (`MaxHealth=3`, `MoveSpeed=100`, no `Idle`/`Hit`/`Death` flipbook
      overrides), so the Snail is not yet the full §6.3 asset.
- [ ] Normal state: use base `PatrolStep` / `LedgeAhead`; no child Tick.
- [ ] `Die` override: if already `bShellPhase`, return; otherwise set shell
      flags (`bShellPhase=true`, `bIsDead=false`, `bInvulnerable=true`,
      `bDealContactDamage=true`, `bAggro=false`), `ContactDamage=1`,
      `MoveSpeed=ShellSpeed`, `MaxWalkSpeed=ShellSpeed`, `bCanMove=true`, play
      shell idle, `Set Life Span(ShellLifetime)`. **Do not call `Parent: Die`.**
- [ ] Shell movement uses the same base `PatrolStep` and `LedgeAhead`; do not
      add a second shell Tick.
- [ ] `Event Hit` handles the wall/edge reaction and plays
      `ShellWallHitFlipbook` → `BackToShellIdle` (`0.25`); ensure normal-state
      wall reversal is not lost.
- [ ] Override `RefreshStateFlipbook`: shell idle while `bShellPhase`; otherwise
      walk/idle.

**Done when:** kill → shell, no destruction; shell sweeps and turns at the
platform edge; shell ignores bullets; contact `1`; destroys itself after `8 s`.

**Do not:** add detection, call `Parent: Die`, or let the shell walk off an edge.

---

### A2a — `BP_RockBase` + `BP_Rock1/2/3` (Owner A2)

**Read:** `EnemyAI.md` §8.2; `Enemies.md` §6.2; `EnemyPlacement.md` §4.2.
**Depends:** M1.

**Status: NOT STARTED (4 Nov 2026).** `BP_RockBase` and `BP_Rock1/2/3` still hold
every base default (`ChaseSpeed=150`, `MoveSpeed=100`, `MaxHealth=3`,
`ContactDamage=1`) and declare zero own variables. No split graph exists, so
`BP_RockBase` in the export is an empty template. **Aggro-on-hit is done (5 Nov):**
`bAggroOnHit=true` is live on all three CDOs; the rest of the card is still open.

**Parallel prep:** `BP_RockBase`/Rock unique variables and Class Defaults may be
prepared now; split/chase graphs wait for A1's `M1 GREEN`.

**Tasks**

- [ ] `BP_RockBase`: add `RockTier`, `ChildRockClass`, `bCanSplit`,
      `SplitImpulse`, `SplitOffset`, `MaxPieces`.
- [ ] Child Class Defaults: health `3/2/1`, `MoveSpeed` `100/140/180`, tier
      `1/2/3`, `ChildRockClass` `Rock2/Rock3/None`, `bCanSplit` `true/true/false`,
      rock flipbooks, positive `ChaseSpeed` per tier (start `120/160/200`).
- [ ] Use base `PatrolStep` / `ChaseStep` / `UpdateAggro`; no child movement
      Tick. Aggro rectangle `700×500`, `DeAggroTime=2.0`.
- [ ] `Die` override: if `bCanSplit` and `ChildRockClass` is valid and the live
      `BP_RockBase` count is `<= MaxPieces - 1`, spawn two children at
      `±SplitOffset`, launch them with `SplitImpulse`; then `Parent: Die`.
- [ ] Split pieces rely on `Landed` / `ResolveKnockback` to adopt the landing
      platform; do not copy the parent's `HomePlatform`.
- [ ] Override `RefreshStateFlipbook`: run when `Abs(Velocity.X) > 10`, else idle.

**Done when:** test 11 passes; kill tier 1 → 2× tier 2; kill tier 2 → 4× tier 3;
tier 3 does not split; live count stays ≤ 8; pieces adopt their landing platform.

**Do not:** copy the stationary turtle; add a second Tick; or assume the parent
platform remains valid.

---

### C5 — `BP_Rhino` (Owner C)

**Read:** `EnemyAI.md` §8.6; `Enemies.md` §6.6; `EnemyPlacement.md` §4.6.
**Depends:** M1.

**Tasks**

- [ ] Add only the unique variables: `bCharging`, `ChargeSpeed`,
      `ChargeDirection`, `WallHitCooldown`, `LastWallHitTime`, `RunFlipbook`,
      `HitWallFlipbook`. **Do not** declare `MoveSpeed`; inherit it.
- [ ] Class Defaults: `MoveSpeed=120`, `ChaseSpeed=600`, `ChargeSpeed=600`,
      `MaxHealth=4`, `CurrentHealth=4`, `bUseHealth=true`,
      `bInvulnerable=true`, `ContactDamage=1`, `AggroHalfWidth=1200`,
      `AggroHalfHeight=500`, `DeAggroTime=2.0`.
- [ ] `BeginPlay`: `InitEnemy`; keep `bInvulnerable=true`; contact on;
      `SetFacing(ChargeDirection)`; `MaxWalkSpeed=MoveSpeed`; idle loop.
- [ ] Override `UpdateAggro`: call `Parent: UpdateAggro`, then set
      `bCharging=bAggro` (do not duplicate detection).
- [ ] `Event Hit`: ignore the player; require `Abs(Normal.X)>0.7`; enforce
      `WallHitCooldown`; subtract 1 health; `SetFacing(-Facing)`; play
      `HitWallFlipbook`; if health `<=0`, `bInvulnerable=false` then `Die`;
      else `EndWallHit` (`0.3`).
- [ ] `EndWallHit` resumes charge/patrol and refreshes the flipbook.
- [ ] Override `RefreshStateFlipbook`: `RunFlipbook` while `bCharging`, else idle.

**Done when:** test 15 passes: bullets do nothing; 4 wall hits kill; it turns
after each hit; contact kills the player; `KillVolume` still destroys it.

**Do not:** add health damage from bullets, vertical movement, or a second
detection box.

---

### C6 — `BP_ToxicSlime` (Owner C)

**Read:** `EnemyAI.md` §8.5; `Enemies.md` §6.5; `EnemyPlacement.md` §4.5.
**Depends:** M1 + C2.

**Tasks**

- [ ] Add only the unique variables: `PuddleClass`, `PuddleInterval`,
      `NextPuddleTime`, `PuddleOffset`, `bLeaveTracks`.
- [ ] Class Defaults: `ChaseSpeed=0`, `MaxHealth=3`, `MoveSpeed=70`,
      `ContactDamage=1`, slime flipbooks.
- [ ] `BeginPlay`: `InitEnemy`; `NextPuddleTime = Get Game Time in Seconds`.
- [ ] Use base `PatrolStep` / `LedgeAhead`; no detection, no child movement Tick.
- [ ] Own `Event Tick` for the puddle only: return if dead, tracks off, or
      `Abs(Velocity.X) < 10`; when the cooldown expires, spawn `PuddleClass` at
      `ActorLocation + PuddleOffset`, then set `NextPuddleTime += PuddleInterval`.
- [ ] Override `RefreshStateFlipbook`: `FLB_Slime_IdleRun` while alive.

**Done when:** puddles spawn only while moving, each disappears after `3 s`,
player dies on contact, no detection, and the slime never walks off a ledge.

**Do not:** add a second movement Tick or a chase branch.

---

## 8. AI assistant handoff prompt

Give your AI assistant the whole repository, then paste the block for your slot.
Replace `<SLOT>` with `A1`, `A2` or `C` and `<ASSET>` with the first asset.
There is **no `B` slot any more**: B's assets are A2's.

```text
You are the AI assistant for Owner <SLOT> on the Unreal Engine 4.27.2 project
"Don't Trust The Levels". The project is Blueprint-only, Paper2D, no C++, no
Behavior Tree, no NavMesh, no EQS.

Read, in this order:
1. Docs/EnemyWorkPlan.md (the assignment, gates and acceptance tests).
2. Docs/EnemyAI.md sections 1-2, 4, 6, 10-11 and the section for your asset.
3. Docs/Enemies.md sections 3-4 and the section for your asset.
4. Docs/EnemyPlacement.md only for placement or M4.
5. Docs/LfsLocking.md before touching a .uasset or .umap.

Current asset: <ASSET>.
Your ownership is exactly the file list for your slot in
Docs/EnemyWorkPlan.md section 4.1. Only edit those exact .uasset paths, plus
the status-log lines the plan allows. Do not edit a shared base or another
owner's asset, or a level map unless the plan explicitly lists it for your slot.
BP_EnemyBase, BP_EnemyPlatform and BP_Snail are A1-only; BP_RockBase, the Rock
children, BP_SpikeTurtle, BP_Ghost, BP_Bat, BP_FloatingSkull and both level maps
are A2-only; BP_ShooterEnemyBase, BP_EnemyProjectile* and BP_ToxicPuddle are
C-only.

Hard rules:
- Lock the asset with Git LFS / UE Source Control before editing. Never co-edit.
- This build cannot create K2 nodes from Python. Do not attempt graph authoring
  with Python. Build nodes, wires, variables and functions manually in the editor.
- One movement authority per asset. Walkers use the base Event Tick; stationary/
  flyers set bCanMove=false and use their own Tick/Launch. ChaseSpeed=0 for
  Turtle/Ghost/Skull; Bat keeps ChaseSpeed=1000 for MaxFlySpeed.
- Do not add a variable that already exists in a parent. Use inherited
  bAggro, AggroRadius, ChaseSpeed, MoveSpeed, KnockbackForce, Facing and the
  base health/contact/flipbook variables. Do not add MaxWalkSpeed.
- Do not add KnowbackForce. Keep KnockbackForce.
- Contact damage goes through ContactBox, not the capsule.
- Compile and save after every function or graph. Never leave a red error.
- Run `py -3 Scripts\_verify_enemy_base.py` after any base-adjacent change;
  the accepted result is 52 PASS / 0 FAIL.
- A1/A2 may prepare unique child variables/defaults, art and static
  map/platform placement, but may not wire walker graphs or run walker PIE
  before A1 posts M1 GREEN.
- If a parent member is missing, stop and report it. Do not duplicate it in the
  child. If two docs disagree, EnemyAI.md wins; report the conflict.

Pre-flight, before any edit:
- State your slot and list the exact `.uasset` paths from §4.1 that you will
  touch.
- Run `git lfs locks` and `git status --short`. If a target is locked by someone
  else, or the working tree contains another owner's changes, stop.
- If any intended path is not in your §4.1 list, stop; do not “just fix” it.
- Never write, rename, move or delete `.uasset`/`.umap` with Python or shell;
  only the Unreal Editor may save them.
- Never run `git add -A`, `git commit -a`, `git reset`, `git clean`,
  `git checkout --`, or `git restore`. Stage only your exact files.
- Do not pull with unsaved editor changes. Close the editor before pulling.

Work one asset at a time. For each asset:
1. Post the lock and the first task.
2. Build the variables and defaults from the work card.
3. Build one function at a time; compile after each.
4. Run the card's PIE acceptance test.
5. Report exact PASS/FAIL, compile status, verifier status and files changed.
6. Commit, push, release the lock, and append a status line.

Stop immediately and report if:
- a parent member is missing or a compile error points at `BP_EnemyBase`;
- a fix would require editing another owner's file;
- the plan and a work card disagree;
- you cannot acquire the lock.

Do not claim a test passed unless you ran it in PIE. Do not invent variable
names, function names or defaults that are not in the linked sections.
```

Owner A1 should also add: `M1 is the gate; post M1 GREEN with verifier output
before wiring Snail. Prepare Snail defaults now, but do not run walker PIE until
M1 GREEN.` Owner A2 should add: `Prepare Rock and Skull defaults and map
placement now; do not wire Rock graphs or run Rock PIE until A1 posts M1 GREEN.
You also own the three finished specials (SpikeTurtle, Ghost, Bat): regression
only, never rebuild them. The first open item is deleting the Ghost's TEMP-M1
bAggro/AggroRadius/ChaseSpeed locals so it inherits them from the base.`
Owner C should add: `Support first; Wood Log patrol/aggro waits for M1; Rhino
before Slime.`

---

## 9. Definition of done (per asset)

An asset is **DONE** only when all are true:

- [ ] Compile is clean and the asset is saved.
- [ ] Every variable in the card exists once, with the exact name, type and
      default; inherited names are not duplicated.
- [ ] Every function/event in the card is wired; no orphan or disabled node that
      the card requires.
- [ ] `BP_EnemyBase` still reports **52 PASS / 0 FAIL / 0 PENDING** with no new
      FAIL (7 Nov 2026: the two `Is Flying` guards of `EnemyAI.md` §7.2 items 4
      and 6 are in and PASS. The `InitEnemy` / `AnyDamage` / `Die` FAILs quoted
      here until 7 Nov 2026 were a bug in the checker, not in the asset:
      `exec_edges()` looked collapsed graphs up by their raw name while
      `parse_nodes()` keys them space-stripped, so every `K2Node_Composite` body
      was invisible — and those three chains keep `Set CurrentHealth`,
      `PlayStateFlipbook` and `SetLifeSpan` inside collapsed nodes. A third
      instance of the same trap hid `FindHomePlatform` itself: `verify()` tested
      the T3D display name `"Find Home Platform"` against the space-free
      `"FindHomePlatform"`, so a guard that had just been built still read as
      PENDING. Both are fixed in `Scripts/_verify_enemy_base.py`; the audit tool
      `Scripts/_audit_enemy_base.py` now expands the same bodies).
- [ ] The card's PIE acceptance test passes; record what you actually observed.
- [ ] No regression in an already-done enemy (contact, health, death, split).
- [ ] The asset is committed and pushed, and the LFS lock is released.
- [ ] The status log has the asset line and any doc deviation.
- [ ] Any changed contract was updated in `EnemyAI.md` / `Enemies.md` by A1 in
      the same commit.

A graph that compiles but has no PIE evidence is **not done**.

---

## 10. Status log

Append one line per asset; do not rewrite another owner's line. Keep the table
sorted by date. Use `PASS`, `FAIL`, `BLOCKED` or `DONE` explicitly.

| Date | Owner | Asset | State | Verifier | PIE test | Commit / note |
|---|---|---|---|---|---|---|
| 24 Oct 2026 | A | plan created | DONE | — | — | `Docs/EnemyWorkPlan.md` |
| 24 Oct 2026 | A | `BP_EnemyPlatform` | PASS | `_verify_enemies.py` 201 PASS / 0 FAIL / 0 WARN | — | `bEnabled=true`, Zone NoCollision/hidden; commit pending |
| 25 Oct 2026 | B | M0 done | DONE | — | — | read-in complete (WorkPlan §3-6, EnemyAI §1-2/§4/§8/§10-11, Enemies §3-4/§6/§7.3, LfsLocking, EnemyPlacement §4.1/4.4/4.7/4.8); merged origin/branch/Dennis into branch/Jones; first asset BP_SpikeTurtle |
| 25 Oct 2026 | B | BP_SpikeTurtle | DONE | n/a | test 10: spike cycle/timers/idle PASS (PrintString evidence); contact kill PASS after Dennis's 744f845 ContactBox fix (fresh side-touch kills in spikes-out window) | ea78feb + merge 0b232e9; B's diagnostic child box deleted; remaining gap (kill-on-already-overlap during phase change) reported to A as base-contract proposal |
| 26 Oct 2026 | A | `BP_EnemyBase` | IN PROGRESS | contact `4 PASS`; kill guard `1 PASS`; base `44 PASS` | drop/contact kills once, one reload | 6/13 AI functions; next aggro set |
| 26 Oct 2026 | B | BP_Ghost | DONE | n/a | tests 12-13 PASS: hidden start (no collision/contact/chase), 550-sphere trigger, through-wall chase (WorldStatic=Ignore), visible/hidden loop forever, 2 hits kill, contact kill while visible, no de-aggro | Ghost art faces left natively: SetFacing input negated in chase; TEMP-M1 locals (bAggro/AggroRadius/ChaseSpeed) declared in child because base M1 has not added them yet - migrate to inherited when A posts M1 GREEN; first-appear GoIdle refresh added (RefreshStateFlipbook 0.5 s after StartAggro) |
| 27 Oct 2026 | A1/A2 | Owner A split | DONE | — | — | A1: `BP_EnemyBase`, `BP_EnemyPlatform`, `BP_Snail`, contract docs; A2: Rocks, `L_Level_01`; §4.2 boundary; walker graphs/PIE wait for M1 |
| 27 Oct 2026 | B | BP_Bat | DONE | n/a | test 14 PASS: hang (CeilingIn -> Hanging loop, no drift), 600-sphere trigger, contact ON during 0.5 s wind-up, direct chase colliding with walls/floors (no WorldStatic=Ignore), 2 hits kill, no de-aggro | DEVIATION: TriggerRadius=600 (card says 300) - deliberate playtest tuning, needs A1's blessing + doc sync; Ghost/Turtle editor resaves ride along (Ghost = byte-noise from f8e6cef adoption; Turtle = capsule Pawn=Block + ToggleIdle removed, both pending A1 ruling) |
| 4 Nov 2026 | A/B | BP_Bat hit retune | DONE | live CDO `KnockbackForce=0`, `TriggerRadius=800`; `RefreshStateFlipbook` 8 nodes | hit no longer slides the Bat along the ceiling or pushes it out of its trigger; it can now enter `CeilingOut` and chase | `BP_Bat.uasset`; docs synced to 800 |
| 4 Nov 2026 | A/B | BP_Bat chase follow-up | DONE | live CDO `KnockbackForce=0`, `TriggerRadius=1000`, `MaxAcceleration=8192`; `ChaseSpeed=1000` | widened the distance trigger so the approach from the playable floor is covered, and made acceleration immediate after the zero-vector hit; damage still does not set `bTriggered`, so a shot from outside `1000` remains idle | `BP_Bat.uasset`; docs synced to 1000/8192 |
| 4 Nov 2026 | A1 | Owner split re-issued | DONE | `_check_enemy_ai_vars.py` **24 PASS / 0 FAIL**; 21 function graphs; 13/13 AI functions | — | `Docs/EnemyWorkPlan.md`; **Owner B retired** — slots are A1/A2/C, B's assets (`BP_SpikeTurtle`, `BP_Ghost`, `BP_Bat`, `BP_FloatingSkull`), `L_Level_Testing` and milestone M2 moved to A2; §0/§3/§4/§4.1/§4.2/§5/§6/§7/§8 updated; A1's next task is the aggro-on-hit base change (`bAggroOnHit`; `HitAggroDuration` was dropped on 4 Nov in favour of reusing `DeAggroTime`) |
| 4 Nov 2026 | A2 | M2 handover | DONE | export + live CDO: zero own variables on `BP_Rock1/2/3`, `BP_Snail`, `BP_WoodLog`, `BP_Rhino`, `BP_ToxicSlime`, `BP_FloatingSkull` | — | A2 inherits three DONE specials (tests 10/12/13/14); open = build `BP_FloatingSkull`, delete the Ghost's TEMP-M1 locals so it inherits `bAggro`/`AggroRadius`/`ChaseSpeed`, and get A1's ruling on the Turtle capsule `Pawn=Block` + removed `ToggleIdle` |
| 5 Nov 2026 | A1 | `BP_EnemyBase` aggro-on-hit | DONE | `UpdateAggro` 54 nodes (46 + 8); fresh export + verifier: 45 PASS / 0 FAIL / 0 PENDING; `_check_enemy_ai_vars.py` 25 PASS / 0 FAIL; `BP_Snail` CDO `ChaseSpeed=80`, `AggroHalfWidth=0`, `AggroHalfHeight=0`, `bAggroOnHit=true` saved and re-read | — | design page `Scripts/_aggro_full_graph.html`; 1 variable (`bAggroOnHit`, `DeAggroTime` reused) + 8 nodes, no new function/local; `_verify_enemy_base.py` now asserts the 3 new links and the 3 old links; Snail health/movement/flipbooks remain open; PIE 1–9 still not logged |
| 5 Nov 2026 | A1/A2 | Gun-aggro consistency | PARTIAL | live CDOs: `BP_Rock1/2/3` and `BP_WoodLog` now `bAggroOnHit=true`; `BP_Snail` already true. Saved and read back; dirty content empty | — | walkers use the base cross-platform hit term and `ChaseStep` walks to the ledge (closest safe X). `BP_Bat` is the one flying gun-aggroable enemy; its 13-node `RefreshStateFlipbook` hit branch is staged in `Scripts/_bp_bat_refresh_modified.txt` but the Function Entry → branch wire is still open, so a hit from outside `TriggerRadius=1000` still hangs. `Rhino`/`Ghost`/`SpikeTurtle`/`FloatingSkull` are not gun-aggroable; `ToxicSlime` cannot be aggroed at all | `BP_Rock1/2/3.uasset`, `BP_WoodLog.uasset`, `Enemies.md`, `EnemyAI.md` |
| 5 Nov 2026 | A2 | `BP_Bat` three-bug follow-up | DONE | issues 1–3 verified in PIE; live `RefreshStateFlipbook` has the 13-node hit branch + `MaxFlySpeed=ChaseSpeed`; EventGraph `HangIdle` gated on `bTriggered` | — | live CDO `TriggerRadius=1000`, `ChaseSpeed=1000`, `MaxFlySpeed=400`, `MaxAcceleration=8192`; staged 17-node patch remains available for a clean re-paste | `Enemies.md` §6.8, `EnemyAI.md` §8.8 |
| 7 Nov 2026 | A2 | `BP_Bat` Level 1 instance | DONE | headless export + CDO readback: hit branch, `HangIdle` gate and `MaxFlySpeed` write all intact (17-node `RefreshStateFlipbook`); `L_Level_01` instance was at `Y=-100` vs terrain `Y=0` (`TM_Background`, 200 uu BlockAll slab; `ortho_width=3000`) | — | the Y offset put the sprite behind the terrain plane (invisible under tiles) and the capsule ~70 uu inside the collision slab (slow / ejected behind walls); moved the instance to `Y=0` | `L_Level_01.umap`, `Enemies.md` §6.8, `EnemyPlacement.md` §2 |
| 7 Nov 2026 | A2 | `BP_Bat` slow after a hit (2nd pass) | DONE (A1 row below) | live T3D export: `BP_EnemyBase.K2Node_CallFunction_28.bZOverride = false`; `BP_Bat` has no `SetMovementMode`; `Scripts/_check_bat_hit_knockback.py` → FAIL. Live CDOs: `BP_Bat` is the only `KnockbackForce=0` (`MoveSpeed=100`, `MaxWalkSpeed=0`, `MaxFlySpeed=400`) | — | `bZOverride=false` makes the launch inherit the Bat's own Z velocity, so `HandlePendingLaunch()` forces `MOVE_Falling`; the cap becomes `MaxWalkSpeed = MoveSpeed = 100` and only `AirControl` (0.05) X/Y input applies, so `MaxFlySpeed=1000` never matters → the Bat crawls until it lands. Fix = base `bZOverride=true` (root cause; grounded walkers unchanged) or the pre-wired Bat Tick guard `Scripts/_bp_bat_flying_guard_paste.txt`; PIE pending | `Enemies.md` §4.2/§6.8, `EnemyAI.md` §7.1/§8.8, `Scripts/_check_bat_hit_knockback.py`, `Scripts/_bp_bat_flying_guard_paste.txt` |
| 7 Nov 2026 | A1 | `BP_EnemyBase` knockback Z override | DONE | live T3D export: `K2Node_CallFunction_28.bZOverride = true`; `Scripts/_check_bat_hit_knockback.py` → `RESULT: PASS (A: bZOverride=true)`; `_verify_enemy_base.py` 45 PASS / 0 FAIL / 0 PENDING | — | the shared `AnyDamage` launch no longer inherits the victim's Z velocity, so a flying enemy with `KnockbackForce=0` keeps `MOVE_Flying` and `MaxFlySpeed`; grounded walkers are unchanged (`Vz ≈ 0`); the Option-B Bat Tick guard is not in the asset and is not needed; closes the A2 row above. Commit `BP_EnemyBase.uasset` + docs, push, then re-run PIE 7/8/14 | `BP_EnemyBase.uasset`, `Enemies.md` §4.2/§6.8, `EnemyAI.md` §7.1/§8.8, `EnemyWorkPlan.md` |
| 7 Nov 2026 | A1 | Knockback retune (shared `AnyDamage`) | DONE | `Scripts/_run_enemy_tuning.py` → live CDO `BP_EnemyBase.KnockbackForce` 200 → 1200, saved and re-read; `Scripts/_run_knockback_lift_check.py` → `RESULT: PASS` (`MakeVector.Z ← Multiply(KnockbackForce, 0.4)`, `lift=480 uu air=0.327 s shove=392 uu`) | PIE pending | a horizontal-only launch is worth ~15 uu at *any* force (`ApplyVelocityBraking` caps the victim at `MaxWalkSpeed` with `GroundFriction^2 * BrakingDecelerationWalking` = `131072` uu/s², then `GroundFriction` 8 kills the rest), so the shove now carries an authored arc: `MakeVector.Z = KnockbackForce * 0.4` via `Scripts/_bp_enemy_base_knockback_lift_paste.txt` → `Lift 480`, `t_air 0.327 s`, ~392 uu at `GravityScale=3`. `BP_Bat` (`KnockbackForce=0`) still sends a zero vector, so the `bZOverride=true` fix above is untouched. Gotcha: every `Content/**` file is read-only on disk after a git operation — `save_loaded_asset` returns `False` until the flag is cleared | `BP_EnemyBase.uasset`, `Enemies.md` §4.2, `EnemyAI.md` §7.1, `Scripts/_set_enemy_tuning.py`, `Scripts/_check_knockback_lift.py`, `Scripts/_bp_enemy_base_knockback_lift_paste.txt` |
| 7 Nov 2026 | A1 | `BP_Snail` chase speed | DONE | `Scripts/_run_enemy_tuning.py` → live CDO `BP_Snail.ChaseSpeed` 80 → 250, saved and re-read; aggro box still `0/0`, `bAggroOnHit=true` | PIE pending | `UpdateAggro`'s chase branch writes `MaxWalkSpeed = ChaseSpeed` (patrol writes `MoveSpeed`), so the old `80` uu/s against the player's `1000` uu/s was indistinguishable from standing still. No proximity aggro was added: the zero aggro box plus `bAggroOnHit` is the locked §13 design (a snail ignores a player until it is shot) | `BP_Snail.uasset`, `Enemies.md` §6.3, `EnemyAI.md` §8.3/§10, `EnemyWorkPlan.md` |
| 7 Nov 2026 | A1 | `BP_EnemyBase` acquire/keep split | IN PROGRESS | whole-graph paste applied: live T3D `Update Aggro` is 61 nodes, **1 piece**, 10 of 11 checks PASS — the six new→old links landed. The editor renamed the pasted `FunctionEntry` (`K2Node_FunctionEntry_0` → `_4`), so the importer dropped **five** entry wires, not the three that were first noticed: `FunctionEntry.Player` → `IsPlayerInAggroBox.Player` `(592,-640)`, → `IsPlayerOnHomePlatform.Player` `(880,-640)`, → `K2_GetActorLocation.self` `(592,-288)` (the *player* location; the second `K2_GetActorLocation` at `(592,-432)` is the enemy's own and must stay unwired), → `ChaseStep.Player` `(4208,-960)`, and `FunctionEntry.Delta Seconds` → `Add.A` `(3440,-480)` (without it `UnreachableTime += dt` becomes `+= 0`, so a walker would never de-aggro). The `then` wire survived. The regenerated paste writes all five on both pins and `Scripts/_test_full_paste.py` PASSes 11/11 both as-is and with the entry renamed on purpose | drag those five wires (entry `(96,-752)`) or re-paste `Scripts/_bp_enemy_base_updateaggro_full_paste.txt` → compile → save → `_run_aggro_keep_check.py` = PASS → PIE | the box term is acquire-only now: `Chase = Detect OR (bAggro AND Keep)` where `Keep = OnHome AND |ΔZ| ≤ MaxChaseStepZ (+ hit window + AggroRadius > 0)`. A walker used to de-aggro after `DeAggroTime` whenever the player ran past `AggroHalfWidth` on the *same* platform, because acquire and keep shared one 600–1400 uu rectangle. Flyers are unaffected (they never call `UpdateAggro`) and the `AggroRadius > 0` term keeps that guarantee inside the shared rule | `Scripts/_bp_enemy_base_updateaggro_full_paste.txt`, `Scripts/_make_full_aggro_paste.py`, `Scripts/_test_full_paste.py`, `Scripts/_make_aggro_paste_graph.py`, `Scripts/_check_aggro_keep.py`, `Scripts/_run_aggro_keep_check.py`, `Scripts/_verify_enemy_base.py`, `EnemyAI.md` §1/§4/§6.2/§6.3/§6.4, `Enemies.md` §5.1/§7.3 |
| 7 Nov 2026 | A1 | `BP_EnemyBase` flyer guards | DONE | `_verify_enemy_base.py` **52 PASS / 0 FAIL / 0 PENDING** — both `Is Flying` guards present; `_audit_enemy_base.py` 50 graphs / 23 composites / **11 unwired (0 suspicious)** / 0 orphans; walker rescue PIE-confirmed (9a) | 9a PASS (walker); 9b PASS (flyers — no flyer sent back to a zone) | `TryRescue` and `FindHomePlatform` now return immediately for `MOVE_Flying`, so a flyer is never snapped to a zone and never adopts one. Three checker bugs fixed in the same session, all the same `gnorm()` trap: `exec_edges()` looked a composite's `BoundGraph` up by raw name (3 false FAILs, 23 composite bodies invisible), `verify()` tested the T3D display name `"Find Home Platform"` (a built guard still read PENDING), and the audit counted `K2Node_ComponentBoundEvent` as an orphan. `_probe_rescue.py` no longer hard-codes `guard PENDING`: it reads `_verify_enemy_base_out.txt` (`guards_built()`), covered by `Scripts/_test_probe_guards.py` |
| 8 Nov 2026 | A1 | M1 PIE walker tests 1–7 | DONE (8–9 pending) | `_check_aggro_keep.py` re-run 8 Nov 2026 on the post-guard export: 11/11 PASS — the five `FunctionEntry` wires of the row above are present (`FunctionEntry drives Tick, both player pins and the clock — 6 wires present`); `_verify_enemy_base.py` 52 PASS / 0 FAIL / 0 PENDING | 1–4, 6, 7 PASS with no deviation; 5 PASS — the walker halts where it is and faces the player instead of walking to the ledge, then patrols again after `DeAggroTime` (the `False → bAggro` branch); 8–9 not run: no staircase located in `L_Level_01`, and 9's precondition (no zone within `RescueRadius`) cannot be met there | closes the acquire/keep row above; `EnemyAI.md` §11 rows 1–7, §6.3, §12 |



**Defect report (B → A1, 25 Oct 2026) — `BP_EnemyBase` contact chain cannot fire.**
Binary inspection of the committed `BP_EnemyBase.uasset` (458 KB, commit
`8505b35`) shows only three SCS components (`CollisionCylinder`, `Sprite0`,
`CharMoveComp`). **No `ContactBox` component exists**, and the contact chain
("Is Overlapped Actor a Player?" → "Is Player Killable" → Kill/ApplyDamage) is
bound to `ReceiveActorBeginOverlap`. Both `BP_EnemyBase` and `BP_Player` use the
`Pawn` preset with `Pawn = Block`, so per `EnemyAI.md` §9 the overlap event never
fires and no enemy can kill the player on contact. PIE evidence (Owner B,
`L_Level_Testing`): `BP_SpikeTurtle` spike cycle/timers work; fresh side-touch
during the spikes-out window does not kill the player; stomping the turtle
kills the turtle via the player's `Event Hit`/Kill path (turtle `bInvulnerable`
was reset by `InitEnemy`; B re-asserts it in the child BeginPlay). The docs'
"ContactBox done 24 Oct / 44 PASS" claim does not match the committed asset,
and `Scripts/_verify_enemy_base.py`, `_make_enemies.py`, `_verify_enemies.py`
are not in any branch's history. Requested from A1: add `ContactBox`
(`BoxComponent`, QueryOnly, Generate Overlap Events, `Pawn=Overlap`, all other
channels Ignore, extents ~`(50,50,90)`), rebind the existing contact chain to
`On Component Begin Overlap (ContactBox)`, re-run the base verifier, commit
`BP_EnemyBase.uasset` + the verifier scripts. B's four assets need no changes
once the base fix lands; B will re-run test 10 and flip the status line.

**Resolved.** `ContactBox` exists on `BP_EnemyBase` and the turtle's contact kill
passed in PIE after the 744f845 fix (see the 25 Oct `BP_SpikeTurtle` row). No
further action; the report is kept for history.

**Current gate:** `M1` is not green, but the code is no longer the blocker.
`BP_EnemyPlatform` is PASS, and `BP_EnemyBase` now has **13/13** AI functions,
**25/25** §4 variables (24 verified on 4 Nov; `bAggroOnHit` is in the asset and
`EXPECTED` grew to 25 rows with it — re-run `_check_enemy_ai_vars.py`) and a
wired `Event Tick`. What is
missing is the PIE evidence for tests 1–9 and the `M1 GREEN` line itself. Do not
wire walker graphs or run walker PIE until that line exists; non-behavioral
Snail/Rock/Skull/map preparation is allowed.

---

## 11. Commit and lock checklist

1. `git lfs locks` — confirm the asset is not locked by someone else.
2. Lock the exact path from **§4.1** in UE Source Control (or
   `git lfs lock <path>`). Do not lock a folder or another owner’s file.
3. Edit; compile; save; PIE; run the verifier.
4. `git status --short` — only your asset, its child, and approved docs.
5. `git add <your exact files>`; never `git add -A` or `git commit -a`.
   Commit with a scoped message:
   `feat(enemy): implement Ghost aggro/visibility loop`
   `feat(enemy): add Rock split tiers`
   `feat(enemy): add projectile and toxic puddle`
   `docs(enemy): sync AI work plan and duplicate variable rules`
6. `git push` — this releases the LFS lock; verify with `git lfs locks`.
7. Append the status line and tell A1 if a contract changed.

Never commit `Saved/`, `Intermediate/`, `DerivedDataCache/`, `__pycache__/`,
probe dumps, or a `.umap` you do not own.

---

## 12. Priority and scope if time slips

The full target remains all nine mechanics. If the schedule slips, keep this
order:

1. **Must-have V1:** M1 base gate (A1), `BP_Snail` (A1), `BP_Rock1/2/3` (A2),
   `BP_WoodLog` (C), `BP_Rhino` (C). `BP_Ghost` (A2) and `BP_Bat` (A2) are
   already DONE, so they cost no remaining time.
2. **Cheap and worth keeping:** `BP_SpikeTurtle` (A2 — already DONE; timers
   only, no movement).
3. **Defer last:** `BP_FloatingSkull` (A2), `BP_ToxicSlime` (C).

Do not “save time” by skipping M1, duplicating movement into a child, or letting
a walker ignore a ledge. Those shortcuts create the exact bugs the AI design
exists to prevent.

---

## 13. Open decisions locked by this plan

These are deliberate, and the technical docs must agree with them:

- `bCanMove` is the shared walker-AI gate. Stationary/flyers set it false; their
  own movement still works.
- `ChaseSpeed <= 0` means “no detection”: Toxic Slime patrols only. Snail is the
  exception introduced by the hit-window decision below (`ChaseSpeed=250` with a
  zero-size aggro box).
- Snail's shell uses base `PatrolStep`; there is no second shell Tick.
- Wood Log stops by setting `bCanShoot=false` and `bCanMove=false` in
  `TryFire`; `EndAttack` restores both. It overrides `ChaseStep` to stand.
- Ghost inherits `bAggro` and `AggroRadius`; Bat inherits `ChaseSpeed`; Rhino
  inherits `MoveSpeed`.
- `BP_PeaPlant` and `BP_EnemyProjectile_Pea` remain unused shells.
- The first PIE gate is a temporary `BP_Rock1` on P_02 or `BP_Snail` on P_00,
  not the current Snail placement at `(-451, 9, 225)`. A2 stages/removes it;
  A1 runs the PIE check without saving the map.
- **Locked 4 Nov 2026 (A1-owned), contracts updated, PIE pending:** aggro on a
  bullet hit. `bAggroOnHit` (bool, `false`) in the base; the post-hit window is
  the existing `DeAggroTime` (`2.0`), deliberately shared with the box de-aggro
  so there is one grace knob and not two. Enabled only on `BP_Rock1/2/3`,
  `BP_WoodLog` and `BP_Snail`.
  The Snail rule above is therefore replaced by `ChaseSpeed=250` with
  `AggroHalfWidth=0` / `AggroHalfHeight=0` and `bAggroOnHit=true`;
  `EnemyAI.md` §4/§6.2/§6.3/§8.2/§8.3/§8.9 and `Enemies.md`
  §4.2/§5.3/§6.2/§6.3 now describe it. Ghost and Rhino stay detection-only and
  bullet-immune. The 8 new nodes and the `BooleanOR` re-wire are in
  `BP_EnemyBase` in the same commit; the acceptance is 54 nodes in a fresh
  `UpdateAggro` export (46 + 8), **45 PASS / 0 FAIL** from
  `_verify_enemy_base.py` (including the 3 new / 3 old link audit) and
  **25 PASS / 0 FAIL** from `_check_enemy_ai_vars.py`. `BP_Snail` carries the
  aggro CDO flip in that same commit.

If implementation proves a decision wrong, A1 updates this list and the matching
contract in the same commit. A2 and C do not fork the design silently.
